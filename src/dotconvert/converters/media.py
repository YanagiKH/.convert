from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from ..errors import ExternalToolError
from ..registry import normalize_extension

AUDIO_TARGETS = {".mp3", ".wav", ".flac", ".ogg", ".aac", ".m4a"}
VIDEO_TARGETS = {".mp4", ".mkv", ".webm", ".mov", ".avi"}


def find_ffmpeg() -> str | None:
    configured = os.environ.get("DOTCONVERT_FFMPEG")
    if configured and Path(configured).is_file():
        return configured
    return shutil.which("ffmpeg")


def _codec_args(target: str) -> list[str]:
    if target == ".mp3":
        return ["-vn", "-c:a", "libmp3lame", "-q:a", "2"]
    if target == ".wav":
        return ["-vn", "-c:a", "pcm_s16le"]
    if target == ".flac":
        return ["-vn", "-c:a", "flac"]
    if target == ".ogg":
        return ["-vn", "-c:a", "libvorbis", "-q:a", "6"]
    if target == ".aac":
        return ["-vn", "-c:a", "aac", "-b:a", "192k"]
    if target == ".m4a":
        return ["-vn", "-c:a", "aac", "-b:a", "192k"]
    if target == ".mp4":
        return ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart"]
    if target == ".mkv":
        return ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "192k"]
    if target == ".webm":
        return ["-c:v", "libvpx-vp9", "-crf", "31", "-b:v", "0", "-c:a", "libopus", "-b:a", "128k"]
    if target == ".mov":
        return ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "192k"]
    if target == ".avi":
        return ["-c:v", "mpeg4", "-q:v", "4", "-c:a", "libmp3lame", "-q:a", "3"]
    raise ExternalToolError(f"Unsupported media target: {target}")


def convert_media(source: Path, destination: Path, target_extension: str) -> None:
    executable = find_ffmpeg()
    if executable is None:
        raise ExternalToolError(
            "FFmpeg was not found. Install FFmpeg or set DOTCONVERT_FFMPEG to the ffmpeg executable path."
        )
    target = normalize_extension(target_extension)
    command = [
        executable,
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source),
        "-map_metadata",
        "0",
        *_codec_args(target),
        str(destination),
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=60 * 60,
            shell=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ExternalToolError(f"FFmpeg could not complete the conversion: {exc}") from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip().splitlines()
        concise = detail[-1] if detail else "unknown FFmpeg error"
        raise ExternalToolError(f"Media conversion failed: {concise}")
