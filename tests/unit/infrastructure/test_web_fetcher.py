import httpx
import pytest

from podforge.domain.value_objects.source_config import SourceConfig, SourceKind
from podforge.infrastructure.adapters.web_fetcher import WebFetcher

SIMPLE_HTML = """\
<html>
<head><title>Title Tag Text</title></head>
<body>
  <nav><a href="/">Home</a></nav>
  <article>
    <h1>Article Heading</h1>
    <p>This is the main body of the article with some interesting content.</p>
    <p>It continues with more detail about the topic at hand.</p>
  </article>
  <footer>Copyright 2026</footer>
</body>
</html>"""

MAIN_TAG_HTML = """\
<html>
<head><title>Main Tag Page</title></head>
<body>
  <nav><a href="/">Home</a></nav>
  <main>
    <h1>Main Content Heading</h1>
    <p>This content lives inside a main tag, not an article tag.</p>
  </main>
</body>
</html>"""

MINIMAL_HTML = """\
<html>
<body>
  <p>Just some body text without semantic tags.</p>
  <p>More text in the body to ensure extraction works.</p>
</body>
</html>"""

EMPTY_HTML = """\
<html>
<head><title>Empty</title></head>
<body>
  <nav>Nav only</nav>
</body>
</html>"""

OG_TITLE_HTML = """\
<html>
<head>
  <meta property="og:title" content="OG Title Wins" />
  <title>Fallback Title</title>
</head>
<body><article><p>Content here.</p></article></body>
</html>"""

H1_ONLY_HTML = """\
<html>
<head></head>
<body>
  <h1>Heading As Title</h1>
  <article><p>Article content with only an h1 for title.</p></article>
</body>
</html>"""

NO_TITLE_HTML = """\
<html>
<body>
  <article><p>Content with no title metadata at all.</p></article>
</body>
</html>"""


def _source() -> SourceConfig:
    return SourceConfig(name="Test", kind=SourceKind.WEB_PAGE, url="http://example.com")


def _fetcher_with_response(html: str, status_code: int = 200) -> WebFetcher:
    """Build a WebFetcher backed by a mock httpx transport."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, text=html)

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    return WebFetcher(client=client)


class TestWebFetcherExtraction:
    def test_extracts_article_tag_content(self) -> None:
        fetcher = _fetcher_with_response(SIMPLE_HTML)
        articles = fetcher.fetch(_source())

        assert len(articles) == 1
        assert "main body of the article" in articles[0].content

    def test_prefers_title_tag_over_h1(self) -> None:
        fetcher = _fetcher_with_response(SIMPLE_HTML)
        articles = fetcher.fetch(_source())
        assert articles[0].title == "Title Tag Text"

    def test_extracts_main_tag_content(self) -> None:
        fetcher = _fetcher_with_response(MAIN_TAG_HTML)
        articles = fetcher.fetch(_source())

        assert len(articles) == 1
        assert "inside a main tag" in articles[0].content

    def test_strips_nav_and_footer(self) -> None:
        fetcher = _fetcher_with_response(SIMPLE_HTML)
        articles = fetcher.fetch(_source())

        assert "Home" not in articles[0].content
        assert "Copyright" not in articles[0].content

    def test_falls_back_to_body(self) -> None:
        fetcher = _fetcher_with_response(MINIMAL_HTML)
        articles = fetcher.fetch(_source())

        assert len(articles) == 1
        assert "body text" in articles[0].content

    def test_returns_empty_for_no_content(self) -> None:
        fetcher = _fetcher_with_response(EMPTY_HTML)
        articles = fetcher.fetch(_source())
        assert articles == []

    def test_prefers_og_title(self) -> None:
        fetcher = _fetcher_with_response(OG_TITLE_HTML)
        articles = fetcher.fetch(_source())
        assert articles[0].title == "OG Title Wins"

    def test_falls_back_to_h1_title(self) -> None:
        fetcher = _fetcher_with_response(H1_ONLY_HTML)
        articles = fetcher.fetch(_source())
        assert articles[0].title == "Heading As Title"

    def test_untitled_when_no_title_metadata(self) -> None:
        fetcher = _fetcher_with_response(NO_TITLE_HTML)
        articles = fetcher.fetch(_source())
        assert articles[0].title == "Untitled"

    def test_sets_source_metadata(self) -> None:
        fetcher = _fetcher_with_response(SIMPLE_HTML)
        source = _source()
        articles = fetcher.fetch(source)

        assert articles[0].source_url == source.url
        assert articles[0].source_name == source.name

    def test_raises_on_http_error(self) -> None:
        fetcher = _fetcher_with_response("Not Found", status_code=404)
        with pytest.raises(httpx.HTTPStatusError):
            fetcher.fetch(_source())
