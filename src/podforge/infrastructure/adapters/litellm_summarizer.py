import logging

import litellm

from podforge.domain.entities.article import Article
from podforge.infrastructure.prompts import (
    build_summarizer_system,
    build_summarizer_user,
)

logger = logging.getLogger(__name__)


class LitellmSummarizer:
    def __init__(
        self,
        model: str = "anthropic/claude-haiku-4-5-20251001",
        show_prompt: str = "",
    ) -> None:
        self._model = model
        self._show_prompt = show_prompt

    def summarize(self, articles: list[Article]) -> str:
        articles_text = "\n\n---\n\n".join(
            f"**{a.title}** ({a.source_name})\n{a.content}" for a in articles
        )
        logger.info("Summarizing %d articles with %s", len(articles), self._model)

        response = litellm.completion(
            model=self._model,
            messages=[
                {
                    "role": "system",
                    "content": build_summarizer_system(self._show_prompt),
                },
                {
                    "role": "user",
                    "content": build_summarizer_user(articles_text),
                },
            ],
        )

        content: str | None = response.choices[0].message.content
        if not content:
            raise RuntimeError("Summarizer returned empty response")
        return content
