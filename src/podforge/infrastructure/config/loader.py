from pathlib import Path

import yaml
from pydantic import BaseModel

from podforge.domain.entities.podcast import Podcast
from podforge.domain.value_objects.host_config import HostConfig
from podforge.domain.value_objects.source_config import (
    SourceConfig,
    SourceKind,
)
from podforge.domain.value_objects.speech_provider import SpeechProvider


class SourceConfigModel(BaseModel):
    name: str
    kind: str
    url: str
    auth: str | None = None


class HostConfigModel(BaseModel):
    name: str
    personality: str
    voice_id: str
    voice_provider: str = "elevenlabs"


class ProviderModel(BaseModel):
    provider: str
    model: str | None = None


class SpeechProviderModel(BaseModel):
    provider: SpeechProvider


class ProvidersModel(BaseModel):
    summarizer: ProviderModel
    script_writer: ProviderModel
    speech: SpeechProviderModel


class DestinationModel(BaseModel):
    kind: str
    path: str | None = None
    channel: str | None = None


class PodcastConfigModel(BaseModel):
    name: str
    schedule: str = "0 7 * * *"
    target_length_minutes: int = 10
    show_prompt: str = ""


class ConfigModel(BaseModel):
    podcast: PodcastConfigModel
    sources: list[SourceConfigModel]
    hosts: list[HostConfigModel]
    providers: ProvidersModel
    destinations: list[DestinationModel]


def load_config(config_path: str) -> tuple[Podcast, ConfigModel]:
    raw = yaml.safe_load(Path(config_path).read_text())
    config = ConfigModel(**raw)

    podcast = Podcast(
        name=config.podcast.name,
        sources=[
            SourceConfig(
                name=s.name,
                kind=SourceKind(s.kind),
                url=s.url,
                auth=s.auth,
            )
            for s in config.sources
        ],
        hosts=[
            HostConfig(
                name=h.name,
                personality=h.personality,
                voice_id=h.voice_id,
                voice_provider=h.voice_provider,
            )
            for h in config.hosts
        ],
        target_length_minutes=config.podcast.target_length_minutes,
        schedule=config.podcast.schedule,
        show_prompt=config.podcast.show_prompt,
    )

    return podcast, config
