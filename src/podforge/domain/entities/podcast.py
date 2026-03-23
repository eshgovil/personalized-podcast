from dataclasses import dataclass, field
from uuid import UUID, uuid5

from podforge.domain.value_objects.host_config import HostConfig
from podforge.domain.value_objects.source_config import SourceConfig

# Fixed namespace for deterministic podcast IDs based on name
_PODCAST_NAMESPACE = UUID("a3bb189e-8bf9-3888-9912-ace4e6543002")


@dataclass
class Podcast:
    name: str
    sources: list[SourceConfig]
    hosts: list[HostConfig]
    target_length_minutes: int = 10
    schedule: str = "0 7 * * *"
    show_prompt: str = ""
    id: UUID = field(init=False)

    def __post_init__(self) -> None:
        self.id = uuid5(_PODCAST_NAMESPACE, self.name)
