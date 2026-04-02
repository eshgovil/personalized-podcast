import json
import logging
from datetime import date, datetime
from pathlib import Path
from uuid import UUID

from podforge.domain.entities.article import Article
from podforge.domain.entities.episode import Episode
from podforge.domain.value_objects.episode_status import EpisodeStatus
from podforge.domain.value_objects.script_segment import (
    ScriptSegment,
    SegmentType,
)

logger = logging.getLogger(__name__)


class JsonEpisodeStore:
    def __init__(self, store_dir: str = ".podcast_data/episodes") -> None:
        self._store_dir = Path(store_dir)
        self._store_dir.mkdir(parents=True, exist_ok=True)

    def save(self, episode: Episode) -> None:
        path = self._episode_path(episode.podcast_id, episode.date)
        data = self._serialize(episode)
        path.write_text(json.dumps(data, indent=2, default=str))
        logger.debug("Saved episode %s (status: %s)", episode.id, episode.status)

    def load(self, podcast_id: UUID, target_date: date) -> Episode | None:
        path = self._episode_path(podcast_id, target_date)
        if not path.exists():
            return None
        data = json.loads(path.read_text())
        return self._deserialize(data)

    def _episode_path(self, podcast_id: UUID, target_date: date) -> Path:
        return self._store_dir / f"{podcast_id}_{target_date.isoformat()}.json"

    def _serialize(self, episode: Episode) -> dict[str, object]:
        return {
            "id": str(episode.id),
            "podcast_id": str(episode.podcast_id),
            "date": episode.date.isoformat(),
            "status": episode.status.value,
            "summary": episode.summary,
            "audio_path": episode.audio_path,
            "summarizer_model": episode.summarizer_model,
            "script_model": episode.script_model,
            "speech_provider": episode.speech_provider,
            "articles": [
                {
                    "id": str(a.id),
                    "title": a.title,
                    "content": a.content,
                    "source_url": a.source_url,
                    "source_name": a.source_name,
                    "published_at": (
                        a.published_at.isoformat() if a.published_at else None
                    ),
                }
                for a in episode.articles
            ],
            "script": [
                {
                    "host_name": s.host_name,
                    "text": s.text,
                    "segment_type": s.segment_type.value,
                }
                for s in episode.script
            ],
        }

    def _deserialize(self, data: dict[str, object]) -> Episode:
        articles_data: list[dict[str, object]] = data.get("articles", [])  # type: ignore[assignment]
        script_data: list[dict[str, object]] = data.get("script", [])  # type: ignore[assignment]

        articles = [
            Article(
                id=UUID(str(a["id"])),
                title=str(a["title"]),
                content=str(a["content"]),
                source_url=str(a["source_url"]),
                source_name=str(a["source_name"]),
                published_at=(
                    datetime.fromisoformat(str(a["published_at"]))
                    if a.get("published_at")
                    else None
                ),
            )
            for a in articles_data
        ]

        script = [
            ScriptSegment(
                host_name=str(s["host_name"]),
                text=str(s["text"]),
                segment_type=SegmentType(str(s["segment_type"])),
            )
            for s in script_data
        ]

        return Episode(
            id=UUID(str(data["id"])),
            podcast_id=UUID(str(data["podcast_id"])),
            date=date.fromisoformat(str(data["date"])),
            status=EpisodeStatus(str(data["status"])),
            summary=str(data["summary"]) if data.get("summary") else None,
            audio_path=str(data["audio_path"]) if data.get("audio_path") else None,
            summarizer_model=(
                str(data["summarizer_model"]) if data.get("summarizer_model") else None
            ),
            script_model=(
                str(data["script_model"]) if data.get("script_model") else None
            ),
            speech_provider=(
                str(data["speech_provider"]) if data.get("speech_provider") else None
            ),
            articles=articles,
            script=script,
        )
