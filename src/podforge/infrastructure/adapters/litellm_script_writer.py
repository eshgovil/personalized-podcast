import json
import logging

import litellm

from podforge.domain.value_objects.host_config import HostConfig
from podforge.domain.value_objects.script_segment import (
    ScriptSegment,
    SegmentType,
)
from podforge.infrastructure.prompts import (
    build_script_writer_system,
    build_script_writer_user,
)

logger = logging.getLogger(__name__)


class LitellmScriptWriter:
    def __init__(
        self,
        model: str = "anthropic/claude-sonnet-4-6-20250514",
        show_prompt: str = "",
    ) -> None:
        self._model = model
        self._show_prompt = show_prompt

    def write_script(
        self,
        summary: str,
        hosts: list[HostConfig],
        target_length_minutes: int,
    ) -> list[ScriptSegment]:
        host_descriptions = "\n".join(f"- {h.name}: {h.personality}" for h in hosts)

        system_prompt = build_script_writer_system(
            target_length_minutes=target_length_minutes,
            host_descriptions=host_descriptions,
            show_prompt=self._show_prompt,
        )

        logger.info(
            "Generating %d-minute script with %s", target_length_minutes, self._model
        )
        response = litellm.completion(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": build_script_writer_user(summary),
                },
            ],
        )

        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("Script writer returned empty response")
        return self._parse_script(content)

    def _parse_script(self, content: str) -> list[ScriptSegment]:
        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1])

        segments_data = json.loads(content)
        return [
            ScriptSegment(
                host_name=seg["host_name"],
                text=seg["text"],
                segment_type=SegmentType(seg["segment_type"]),
            )
            for seg in segments_data
        ]
