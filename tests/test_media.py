import math
import struct
import wave
from pathlib import Path

import pytest

from dotconvert.converters.media import find_ffmpeg
from dotconvert.engine import ConversionEngine
from dotconvert.models import ConversionPlan


@pytest.mark.skipif(find_ffmpeg() is None, reason="FFmpeg is not installed")
def test_wav_to_mp3_with_ffmpeg(tmp_path: Path) -> None:
    source = tmp_path / "tone.wav"
    destination = tmp_path / "tone.mp3"
    sample_rate = 8000
    with wave.open(str(source), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        frames = bytearray()
        for index in range(sample_rate // 4):
            sample = int(12000 * math.sin(2 * math.pi * 440 * index / sample_rate))
            frames.extend(struct.pack("<h", sample))
        handle.writeframes(bytes(frames))

    ConversionEngine().convert(
        ConversionPlan(source=source, target_extension=".mp3", destination=destination)
    )

    assert destination.stat().st_size > 100
