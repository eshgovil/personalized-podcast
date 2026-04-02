import logging
from collections.abc import Mapping, Sequence
from datetime import date
from pathlib import Path

from podforge.application.ports.audio_mixer import AudioMixer
from podforge.application.ports.content_fetcher import ContentFetcher
from podforge.application.ports.delivery_channel import DeliveryChannel
from podforge.application.ports.episode_store import EpisodeStore
from podforge.application.ports.script_writer import ScriptWriter
from podforge.application.ports.speech_synthesizer import SpeechSynthesizer
from podforge.application.ports.summarizer import Summarizer
from podforge.domain.entities.episode import Episode
from podforge.domain.entities.podcast import Podcast
from podforge.domain.value_objects.episode_status import EpisodeStatus
from podforge.domain.value_objects.source_config import SourceKind

logger = logging.getLogger(__name__)

WORK_DIR = Path(".podcast_data")


class PipelineService:
    def __init__(
        self,
        fetchers: Mapping[SourceKind, ContentFetcher],
        summarizer: Summarizer,
        script_writer: ScriptWriter,
        synthesizer: SpeechSynthesizer,
        mixer: AudioMixer,
        episode_store: EpisodeStore,
        channels: Sequence[DeliveryChannel],
        provider_meta: dict[str, str] | None = None,
    ) -> None:
        self._fetchers = fetchers
        self._summarizer = summarizer
        self._script_writer = script_writer
        self._synthesizer = synthesizer
        self._mixer = mixer
        self._episode_store = episode_store
        self._channels = channels
        self._provider_meta = provider_meta or {}

    def run(
        self,
        podcast: Podcast,
        target_date: date,
        from_stage: EpisodeStatus | None = None,
    ) -> Episode:
        episode = self._resume_or_create(podcast, target_date)

        if from_stage and episode.status != EpisodeStatus.CREATED:
            episode = self._rewind_to(episode, from_stage)

        if episode.status == EpisodeStatus.FAILED:
            raise RuntimeError(f"Episode {episode.id} previously failed")

        if episode.status == EpisodeStatus.CREATED:
            episode = self._fetch_articles(podcast, episode)

        if episode.status == EpisodeStatus.ARTICLES_FETCHED:
            episode = self._summarize(episode)

        if episode.status == EpisodeStatus.SUMMARIZED:
            episode = self._generate_script(podcast, episode)

        if episode.status == EpisodeStatus.SCRIPTED:
            episode = self._synthesize(podcast, episode)

        if episode.status == EpisodeStatus.SYNTHESIZED:
            episode = self._deliver(episode)

        return episode

    def _rewind_to(self, episode: Episode, target: EpisodeStatus) -> Episode:
        stage_order = list(EpisodeStatus)
        current_idx = stage_order.index(episode.status)
        target_idx = stage_order.index(target)
        if target_idx < current_idx:
            logger.info(
                "Rewinding episode from %s to %s",
                episode.status,
                target,
            )
            episode.status = target
            self._episode_store.save(episode)
        return episode

    def _resume_or_create(self, podcast: Podcast, target_date: date) -> Episode:
        existing = self._episode_store.load(podcast.id, target_date)
        if existing:
            logger.info(
                "Resuming episode %s (status: %s)", existing.id, existing.status
            )
            return existing
        episode = Episode(podcast_id=podcast.id, date=target_date)
        self._episode_store.save(episode)
        return episode

    def _fetch_articles(self, podcast: Podcast, episode: Episode) -> Episode:
        logger.info("Fetching articles from %d sources", len(podcast.sources))
        for source in podcast.sources:
            fetcher = self._fetchers.get(source.kind)
            if not fetcher:
                logger.warning("No fetcher registered for source kind %s", source.kind)
                continue
            try:
                articles = fetcher.fetch(source)
                episode.articles.extend(articles)
            except Exception:
                logger.warning("Failed to fetch from %s", source.name, exc_info=True)

        if not episode.articles:
            episode.status = EpisodeStatus.FAILED
            self._episode_store.save(episode)
            raise RuntimeError("No articles fetched from any source")

        episode.status = EpisodeStatus.ARTICLES_FETCHED
        self._episode_store.save(episode)
        logger.info("Fetched %d articles", len(episode.articles))
        return episode

    def _summarize(self, episode: Episode) -> Episode:
        logger.info("Summarizing %d articles", len(episode.articles))
        episode.summary = self._summarizer.summarize(episode.articles)
        episode.summarizer_model = self._provider_meta.get("summarizer_model")
        episode.status = EpisodeStatus.SUMMARIZED
        self._episode_store.save(episode)
        return episode

    def _generate_script(self, podcast: Podcast, episode: Episode) -> Episode:
        logger.info(
            "Generating script for %d-minute episode",
            podcast.target_length_minutes,
        )
        assert episode.summary is not None
        episode.script = self._script_writer.write_script(
            summary=episode.summary,
            hosts=podcast.hosts,
            target_length_minutes=podcast.target_length_minutes,
        )
        episode.script_model = self._provider_meta.get("script_model")
        episode.status = EpisodeStatus.SCRIPTED
        self._episode_store.save(episode)
        logger.info("Generated %d script segments", len(episode.script))
        return episode

    def _synthesize(self, podcast: Podcast, episode: Episode) -> Episode:
        logger.info("Synthesizing %d segments", len(episode.script))
        host_map = {h.name: h for h in podcast.hosts}
        audio_segments: list[bytes] = []

        for segment in episode.script:
            host = host_map[segment.host_name]
            audio = self._synthesizer.synthesize(segment, host)
            audio_segments.append(audio)

        audio_dir = WORK_DIR / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(audio_dir / f"{episode.id}.mp3")

        self._mixer.mix(audio_segments, output_path)
        episode.audio_path = output_path
        episode.speech_provider = self._provider_meta.get("speech_provider")
        episode.status = EpisodeStatus.SYNTHESIZED
        self._episode_store.save(episode)
        logger.info("Audio saved to %s", output_path)
        return episode

    def _deliver(self, episode: Episode) -> Episode:
        assert episode.audio_path is not None
        logger.info("Delivering episode to %d channels", len(self._channels))
        for channel in self._channels:
            try:
                channel.deliver(episode, episode.audio_path)
            except Exception:
                logger.warning("Delivery failed", exc_info=True)

        episode.status = EpisodeStatus.DELIVERED
        self._episode_store.save(episode)
        return episode
