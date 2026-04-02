import io
import logging

import numpy as np
from kokoro import KPipeline  # type: ignore[import-untyped]
from pydub import AudioSegment  # type: ignore[import-untyped]

from podforge.domain.value_objects.host_config import HostConfig
from podforge.domain.value_objects.script_segment import ScriptSegment

logger = logging.getLogger(__name__)

SAMPLE_RATE = 24000


class KokoroSynthesizer:
    def __init__(self, lang_code: str = "a") -> None:
        self._pipeline = KPipeline(lang_code=lang_code)

    def synthesize(self, segment: ScriptSegment, host: HostConfig) -> bytes:
        logger.debug(
            "Synthesizing segment for %s (%d chars) with Kokoro voice %s",
            host.name,
            len(segment.text),
            host.voice_id,
        )

        chunks: list[np.ndarray] = []
        for result in self._pipeline(segment.text, voice=host.voice_id, speed=1):
            # Kokoro yields (graphemes, phonemes, audio) tuples
            audio = result[-1]
            chunks.append(audio)

        if not chunks:
            raise RuntimeError(
                f"Kokoro returned no audio for segment: {segment.text[:50]}"
            )

        combined = np.concatenate(chunks)
        return self._to_mp3_bytes(combined)

    def _to_mp3_bytes(self, audio: np.ndarray) -> bytes:
        # Kokoro outputs float32 [-1, 1] at 24kHz — convert to 16-bit PCM
        pcm = (audio * 32767).astype(np.int16)
        segment = AudioSegment(
            data=pcm.tobytes(),
            sample_width=2,
            frame_rate=SAMPLE_RATE,
            channels=1,
        )
        buf = io.BytesIO()
        segment.export(buf, format="mp3")
        return buf.getvalue()
