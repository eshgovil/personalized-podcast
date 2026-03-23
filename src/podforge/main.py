import os
from datetime import date

from podforge.application.ports.content_fetcher import ContentFetcher
from podforge.application.ports.speech_synthesizer import (
    SpeechSynthesizer,
)
from podforge.application.services.pipeline import PipelineService
from podforge.domain.entities.episode import Episode
from podforge.domain.value_objects.episode_status import EpisodeStatus
from podforge.domain.value_objects.source_config import SourceKind
from podforge.domain.value_objects.speech_provider import SpeechProvider
from podforge.infrastructure.adapters.elevenlabs_synthesizer import (
    ElevenLabsSynthesizer,
)
from podforge.infrastructure.adapters.file_channel import FileChannel
from podforge.infrastructure.adapters.json_episode_store import (
    JsonEpisodeStore,
)
from podforge.infrastructure.adapters.kokoro_synthesizer import (
    KokoroSynthesizer,
)
from podforge.infrastructure.adapters.litellm_script_writer import (
    LitellmScriptWriter,
)
from podforge.infrastructure.adapters.litellm_summarizer import (
    LitellmSummarizer,
)
from podforge.infrastructure.adapters.pydub_mixer import PydubMixer
from podforge.infrastructure.adapters.rss_fetcher import RssFetcher
from podforge.infrastructure.adapters.web_fetcher import WebFetcher
from podforge.infrastructure.config.loader import load_config


def build_and_run(
    config_path: str,
    target_date: date,
    from_stage: EpisodeStatus | None = None,
) -> Episode:
    podcast, config = load_config(config_path)

    # Build LLM model strings in LiteLLM format: "provider/model"
    summarizer_model = (
        f"{config.providers.summarizer.provider}/{config.providers.summarizer.model}"
    )
    script_model = (
        f"{config.providers.script_writer.provider}"
        f"/{config.providers.script_writer.model}"
    )

    # Wire adapters
    fetchers: dict[SourceKind, ContentFetcher] = {
        SourceKind.RSS: RssFetcher(),
        SourceKind.WEB_PAGE: WebFetcher(),
    }
    summarizer = LitellmSummarizer(
        model=summarizer_model, show_prompt=podcast.show_prompt
    )
    script_writer = LitellmScriptWriter(
        model=script_model, show_prompt=podcast.show_prompt
    )
    synthesizer: SpeechSynthesizer
    if config.providers.speech.provider == SpeechProvider.KOKORO:
        synthesizer = KokoroSynthesizer()
    else:
        synthesizer = ElevenLabsSynthesizer(
            api_key=os.environ.get("ELEVEN_API_KEY"),
        )
    mixer = PydubMixer()
    episode_store = JsonEpisodeStore()

    channels = [
        FileChannel(output_dir=dest.path or "./output")
        for dest in config.destinations
        if dest.kind == "file"
    ]

    pipeline = PipelineService(
        fetchers=fetchers,
        summarizer=summarizer,
        script_writer=script_writer,
        synthesizer=synthesizer,
        mixer=mixer,
        episode_store=episode_store,
        channels=channels,
        provider_meta={
            "summarizer_model": summarizer_model,
            "script_model": script_model,
            "speech_provider": config.providers.speech.provider.value,
        },
    )

    return pipeline.run(podcast, target_date, from_stage=from_stage)
