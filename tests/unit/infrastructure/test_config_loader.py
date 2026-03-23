import tempfile

from podforge.infrastructure.config.loader import load_config

MINIMAL_CONFIG = """\
podcast:
  name: "Test Show"
  target_length_minutes: 5

sources:
  - name: "Test"
    kind: rss
    url: "http://example.com/rss"

hosts:
  - name: "Host"
    personality: "Friendly"
    voice_id: "v1"
    voice_provider: "kokoro"

providers:
  summarizer:
    provider: gemini
    model: gemini-3-flash-preview
  script_writer:
    provider: gemini
    model: gemini-3-pro-preview
  speech:
    provider: kokoro

destinations:
  - kind: file
    path: "./output"
"""

CONFIG_WITH_SHOW_PROMPT = """\
podcast:
  name: "Opinionated Tech"
  target_length_minutes: 10
  show_prompt: "Be sarcastic and skip the fluff."

sources:
  - name: "HN"
    kind: rss
    url: "http://example.com/rss"

hosts:
  - name: "Alice"
    personality: "Curious"
    voice_id: "v1"
    voice_provider: "kokoro"

providers:
  summarizer:
    provider: gemini
    model: gemini-3-flash-preview
  script_writer:
    provider: gemini
    model: gemini-3-pro-preview
  speech:
    provider: kokoro

destinations:
  - kind: file
    path: "./output"
"""

CONFIG_WITH_WEB_SOURCE = """\
podcast:
  name: "Mixed Sources"

sources:
  - name: "Blog"
    kind: web_page
    url: "http://example.com/blog"
  - name: "Feed"
    kind: rss
    url: "http://example.com/rss"

hosts:
  - name: "Host"
    personality: "Neutral"
    voice_id: "v1"

providers:
  summarizer:
    provider: gemini
    model: gemini-3-flash-preview
  script_writer:
    provider: gemini
    model: gemini-3-pro-preview
  speech:
    provider: kokoro

destinations:
  - kind: file
    path: "./output"
"""


def _write_config(content: str) -> str:
    """Write config to a temp file and return the path."""
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    tmp.write(content)
    tmp.flush()
    return tmp.name


class TestConfigLoader:
    def test_loads_minimal_config(self) -> None:
        podcast, config = load_config(_write_config(MINIMAL_CONFIG))
        assert podcast.name == "Test Show"
        assert podcast.target_length_minutes == 5
        assert podcast.show_prompt == ""

    def test_loads_show_prompt(self) -> None:
        podcast, _ = load_config(_write_config(CONFIG_WITH_SHOW_PROMPT))
        assert podcast.show_prompt == "Be sarcastic and skip the fluff."

    def test_loads_web_page_source(self) -> None:
        podcast, _ = load_config(_write_config(CONFIG_WITH_WEB_SOURCE))
        assert len(podcast.sources) == 2
        assert podcast.sources[0].kind.value == "web_page"
        assert podcast.sources[1].kind.value == "rss"

    def test_deterministic_podcast_id(self) -> None:
        p1, _ = load_config(_write_config(MINIMAL_CONFIG))
        p2, _ = load_config(_write_config(MINIMAL_CONFIG))
        assert p1.id == p2.id
