from datetime import date

import pytest

from podforge.application.services.pipeline import PipelineService
from podforge.domain.entities.article import Article
from podforge.domain.entities.episode import Episode
from podforge.domain.entities.podcast import Podcast
from podforge.domain.value_objects.episode_status import EpisodeStatus
from podforge.domain.value_objects.host_config import HostConfig
from podforge.domain.value_objects.script_segment import (
    ScriptSegment,
    SegmentType,
)
from podforge.domain.value_objects.source_config import (
    SourceConfig,
    SourceKind,
)
from tests.fakes.fake_audio_mixer import FakeAudioMixer
from tests.fakes.fake_content_fetcher import FakeContentFetcher
from tests.fakes.fake_delivery_channel import FakeDeliveryChannel
from tests.fakes.fake_episode_store import FakeEpisodeStore
from tests.fakes.fake_script_writer import FakeScriptWriter
from tests.fakes.fake_speech_synthesizer import FakeSpeechSynthesizer
from tests.fakes.fake_summarizer import FakeSummarizer

TODAY = date(2026, 3, 22)

SAMPLE_ARTICLES = [
    Article(
        title="Test Article",
        content="Some interesting content about tech.",
        source_url="http://example.com/1",
        source_name="Test Feed",
    ),
]

SAMPLE_SCRIPT = [
    ScriptSegment(
        host_name="Alice",
        text="Welcome to the show!",
        segment_type=SegmentType.INTRO,
    ),
    ScriptSegment(
        host_name="Bob",
        text="Excited to be here.",
        segment_type=SegmentType.INTRO,
    ),
    ScriptSegment(
        host_name="Alice",
        text="Today we have big news.",
        segment_type=SegmentType.DISCUSSION,
    ),
    ScriptSegment(
        host_name="Bob",
        text="That's a wrap!",
        segment_type=SegmentType.OUTRO,
    ),
]


def _make_podcast() -> Podcast:
    return Podcast(
        name="Test Podcast",
        sources=[
            SourceConfig(
                name="Test RSS", kind=SourceKind.RSS, url="http://example.com/rss"
            ),
        ],
        hosts=[
            HostConfig(name="Alice", personality="Curious", voice_id="v1"),
            HostConfig(name="Bob", personality="Skeptical", voice_id="v2"),
        ],
    )


def _make_pipeline(
    articles: list[Article] | None = None,
    store: FakeEpisodeStore | None = None,
    channel: FakeDeliveryChannel | None = None,
) -> tuple[PipelineService, FakeEpisodeStore, FakeDeliveryChannel]:
    store = store or FakeEpisodeStore()
    channel = channel or FakeDeliveryChannel()

    pipeline = PipelineService(
        fetchers={
            SourceKind.RSS: FakeContentFetcher(
                articles if articles is not None else SAMPLE_ARTICLES
            ),
        },
        summarizer=FakeSummarizer(),
        script_writer=FakeScriptWriter(segments=SAMPLE_SCRIPT),
        synthesizer=FakeSpeechSynthesizer(),
        mixer=FakeAudioMixer(),
        episode_store=store,
        channels=[channel],
    )
    return pipeline, store, channel


class TestPipelineEndToEnd:
    def test_produces_delivered_episode(self) -> None:
        pipeline, _, _ = _make_pipeline()
        episode = pipeline.run(_make_podcast(), TODAY)
        assert episode.status == EpisodeStatus.DELIVERED

    def test_fetches_articles(self) -> None:
        pipeline, _, _ = _make_pipeline()
        episode = pipeline.run(_make_podcast(), TODAY)
        assert len(episode.articles) == 1
        assert episode.articles[0].title == "Test Article"

    def test_generates_summary(self) -> None:
        pipeline, _, _ = _make_pipeline()
        episode = pipeline.run(_make_podcast(), TODAY)
        assert episode.summary == "Fake summary of today's news."

    def test_generates_script(self) -> None:
        pipeline, _, _ = _make_pipeline()
        episode = pipeline.run(_make_podcast(), TODAY)
        assert len(episode.script) == 4
        assert episode.script[0].host_name == "Alice"

    def test_sets_audio_path(self) -> None:
        pipeline, _, _ = _make_pipeline()
        episode = pipeline.run(_make_podcast(), TODAY)
        assert episode.audio_path is not None
        assert episode.audio_path.endswith(".mp3")

    def test_delivers_to_channel(self) -> None:
        pipeline, _, channel = _make_pipeline()
        pipeline.run(_make_podcast(), TODAY)
        assert len(channel.delivered) == 1

    def test_persists_final_state(self) -> None:
        pipeline, store, _ = _make_pipeline()
        podcast = _make_podcast()
        pipeline.run(podcast, TODAY)
        loaded = store.load(podcast.id, TODAY)
        assert loaded is not None
        assert loaded.status == EpisodeStatus.DELIVERED


class TestPipelineResume:
    def test_resumes_from_articles_fetched(self) -> None:
        store = FakeEpisodeStore()
        podcast = _make_podcast()

        existing = Episode(
            podcast_id=podcast.id,
            date=TODAY,
            articles=SAMPLE_ARTICLES,
            status=EpisodeStatus.ARTICLES_FETCHED,
        )
        store.save(existing)

        # Empty fetcher — proves pipeline doesn't re-fetch
        pipeline, _, channel = _make_pipeline(articles=[], store=store)
        episode = pipeline.run(podcast, TODAY)

        assert episode.status == EpisodeStatus.DELIVERED
        assert len(episode.articles) == 1

    def test_resumes_from_summarized(self) -> None:
        store = FakeEpisodeStore()
        podcast = _make_podcast()

        existing = Episode(
            podcast_id=podcast.id,
            date=TODAY,
            articles=SAMPLE_ARTICLES,
            summary="Pre-existing summary",
            status=EpisodeStatus.SUMMARIZED,
        )
        store.save(existing)

        pipeline, _, _ = _make_pipeline(store=store)
        episode = pipeline.run(podcast, TODAY)

        assert episode.status == EpisodeStatus.DELIVERED
        assert episode.summary == "Pre-existing summary"

    def test_resumes_from_scripted(self) -> None:
        store = FakeEpisodeStore()
        podcast = _make_podcast()

        existing = Episode(
            podcast_id=podcast.id,
            date=TODAY,
            articles=SAMPLE_ARTICLES,
            summary="Summary",
            script=SAMPLE_SCRIPT,
            status=EpisodeStatus.SCRIPTED,
        )
        store.save(existing)

        pipeline, _, _ = _make_pipeline(store=store)
        episode = pipeline.run(podcast, TODAY)

        assert episode.status == EpisodeStatus.DELIVERED


class TestPipelineMixedSources:
    def test_aggregates_articles_from_multiple_source_kinds(self) -> None:
        rss_article = Article(
            title="RSS Article",
            content="From RSS feed.",
            source_url="http://example.com/rss/1",
            source_name="RSS Feed",
        )
        web_article = Article(
            title="Web Article",
            content="From web page.",
            source_url="http://example.com/page",
            source_name="Blog",
        )
        store = FakeEpisodeStore()
        channel = FakeDeliveryChannel()

        podcast = Podcast(
            name="Mixed Sources",
            sources=[
                SourceConfig(
                    name="RSS Feed",
                    kind=SourceKind.RSS,
                    url="http://example.com/rss",
                ),
                SourceConfig(
                    name="Blog",
                    kind=SourceKind.WEB_PAGE,
                    url="http://example.com/page",
                ),
            ],
            hosts=[
                HostConfig(name="Alice", personality="Curious", voice_id="v1"),
                HostConfig(name="Bob", personality="Skeptical", voice_id="v2"),
            ],
        )

        pipeline = PipelineService(
            fetchers={
                SourceKind.RSS: FakeContentFetcher([rss_article]),
                SourceKind.WEB_PAGE: FakeContentFetcher([web_article]),
            },
            summarizer=FakeSummarizer(),
            script_writer=FakeScriptWriter(segments=SAMPLE_SCRIPT),
            synthesizer=FakeSpeechSynthesizer(),
            mixer=FakeAudioMixer(),
            episode_store=store,
            channels=[channel],
        )

        episode = pipeline.run(podcast, TODAY)
        assert episode.status == EpisodeStatus.DELIVERED
        assert len(episode.articles) == 2
        assert {a.title for a in episode.articles} == {"RSS Article", "Web Article"}


class TestPipelineFailures:
    def test_fails_on_no_articles(self) -> None:
        pipeline, _, _ = _make_pipeline(articles=[])
        with pytest.raises(RuntimeError, match="No articles fetched"):
            pipeline.run(_make_podcast(), TODAY)

    def test_marks_episode_failed_on_no_articles(self) -> None:
        store = FakeEpisodeStore()
        pipeline, _, _ = _make_pipeline(articles=[], store=store)
        podcast = _make_podcast()

        with pytest.raises(RuntimeError):
            pipeline.run(podcast, TODAY)

        loaded = store.load(podcast.id, TODAY)
        assert loaded is not None
        assert loaded.status == EpisodeStatus.FAILED

    def test_raises_on_previously_failed_episode(self) -> None:
        store = FakeEpisodeStore()
        podcast = _make_podcast()

        existing = Episode(
            podcast_id=podcast.id,
            date=TODAY,
            status=EpisodeStatus.FAILED,
        )
        store.save(existing)

        pipeline, _, _ = _make_pipeline(store=store)
        with pytest.raises(RuntimeError, match="previously failed"):
            pipeline.run(podcast, TODAY)
