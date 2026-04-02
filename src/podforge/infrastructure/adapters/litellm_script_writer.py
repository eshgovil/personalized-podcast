import json
import logging

import litellm

from podforge.domain.value_objects.host_config import HostConfig
from podforge.domain.value_objects.script_segment import (
    ScriptSegment,
    SegmentType,
)

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """\
You are a podcast script writer. Write a natural, engaging conversation \
between podcast hosts discussing today's news.

The conversation should feel authentic — hosts can agree, disagree, ask \
follow-up questions, make jokes, and share opinions based on their personalities.

Target length: ~{target_words} words ({target_length_minutes} minutes of audio)

Hosts:
{host_descriptions}

Output ONLY a JSON array of objects with these fields:
- "host_name": the speaking host's name (must match exactly)
- "text": what they say (natural spoken language, not written prose)
- "segment_type": one of "intro", "discussion", "transition", "outro"

Start with an intro where hosts greet listeners, cover the main stories with \
natural back-and-forth discussion, use transitions between topics, and end \
with a brief outro. Keep the dialogue conversational — short turns, reactions, \
and follow-ups feel more natural than long monologues."""


class LitellmScriptWriter:
    def __init__(self, model: str = "anthropic/claude-sonnet-4-6-20250514") -> None:
        self._model = model

    def write_script(
        self,
        summary: str,
        hosts: list[HostConfig],
        target_length_minutes: int,
    ) -> list[ScriptSegment]:
        host_descriptions = "\n".join(f"- {h.name}: {h.personality}" for h in hosts)
        # ~150 words per minute of spoken audio
        target_words = target_length_minutes * 150

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            target_words=target_words,
            target_length_minutes=target_length_minutes,
            host_descriptions=host_descriptions,
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
                    "content": (
                        f"Write a podcast script for this briefing:\n\n{summary}"
                    ),
                },
            ],
        )

        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("Script writer returned empty response")
        return self._parse_script(content)

    def _parse_script(self, content: str) -> list[ScriptSegment]:
        content = content.strip()
        # Strip markdown code block if present
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
