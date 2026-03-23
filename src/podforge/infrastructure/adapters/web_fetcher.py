import logging
from datetime import UTC, datetime

import httpx
from bs4 import BeautifulSoup

from podforge.domain.entities.article import Article
from podforge.domain.value_objects.source_config import SourceConfig

logger = logging.getLogger(__name__)

# CSS selectors for containers that typically hold main article content
_CONTENT_SELECTORS = ["article", "main", '[role="main"]']

_STRIP_TAGS = [
    "script",
    "style",
    "nav",
    "header",
    "footer",
    "aside",
    "form",
    "noscript",
    "iframe",
]

_MIN_LINE_LENGTH = 3


class WebFetcher:
    """Fetches article content from a web page URL."""

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(
            timeout=30,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (compatible; PodForge/0.1; "
                    "+https://github.com/eshgovil/podforge)"
                ),
            },
        )

    def fetch(self, source: SourceConfig) -> list[Article]:
        logger.info("Fetching web page: %s", source.url)
        response = self._client.get(source.url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "lxml")
        title = self._extract_title(soup)
        content = self._extract_content(soup)

        if not content.strip():
            logger.warning("No content extracted from %s", source.url)
            return []

        article = Article(
            title=title,
            content=content,
            source_url=source.url,
            source_name=source.name,
            published_at=datetime.now(tz=UTC),
        )
        logger.info("Extracted article: %s (%d chars)", title, len(content))
        return [article]

    def _extract_title(self, soup: BeautifulSoup) -> str:
        og_title = soup.find("meta", property="og:title")
        if og_title and hasattr(og_title, "get"):
            og_content = og_title.get("content")
            if og_content:
                return str(og_content)

        title_tag = soup.find("title")
        if title_tag and title_tag.string:
            return title_tag.string.strip()

        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)

        return "Untitled"

    def _extract_content(self, soup: BeautifulSoup) -> str:
        for tag in soup.find_all(_STRIP_TAGS):
            tag.decompose()

        # Try semantic content containers first
        for selector in _CONTENT_SELECTORS:
            container = soup.select_one(selector)
            if container:
                return self._clean_text(container.get_text(separator="\n"))

        # Fall back to body
        body = soup.find("body")
        if body:
            return self._clean_text(body.get_text(separator="\n"))

        return self._clean_text(soup.get_text(separator="\n"))

    def _clean_text(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines()]
        lines = [line for line in lines if len(line) >= _MIN_LINE_LENGTH]
        return "\n".join(lines)
