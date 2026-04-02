import logging
import time
from datetime import datetime

import feedparser  # type: ignore[import-untyped]
import httpx

from podforge.domain.entities.article import Article
from podforge.domain.value_objects.source_config import SourceConfig

logger = logging.getLogger(__name__)


class RssFetcher:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(timeout=30)

    def fetch(self, source: SourceConfig) -> list[Article]:
        logger.info("Fetching RSS feed: %s", source.url)
        response = self._client.get(source.url)
        response.raise_for_status()
        feed = feedparser.parse(response.text)
        articles = [self._to_article(entry, source) for entry in feed.entries]
        logger.info("Got %d articles from %s", len(articles), source.name)
        return articles

    def _to_article(
        self, entry: feedparser.FeedParserDict, source: SourceConfig
    ) -> Article:
        content = entry.get("summary", "") or entry.get("description", "")
        published_at = None
        if entry.get("published_parsed"):
            published_at = datetime.fromtimestamp(time.mktime(entry.published_parsed))

        return Article(
            title=entry.get("title", "Untitled"),
            content=content,
            source_url=entry.get("link", source.url),
            source_name=source.name,
            published_at=published_at,
        )
