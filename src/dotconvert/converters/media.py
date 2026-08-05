from __future__ import annotations

import logging
import os
import shutil
import subprocess
from pathlib import Path

from ..errors import ExternalToolError
from ..registry import normalize_extension

LOGGER = logging.getLogger("dotconvert.media")
AUDIO_TARGETS = {
    ".mp3",
    ".wav",
    ".flac",
    ".ogg",
    ".opus",
    ".aac",
    ".m4a",
    ".wma",
    ".aiff",
}
VIDEO_TARGETS = {
    ".mp4",
    ".mkv",
    ".webm",
    ".mov",
    ".avi",
    ".m4v",
    ".flv",
    ".mpeg",
    ".3gp",
    ".ogv",
    ".ts",
}


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
    if target == ".opus":
        return ["-vn", "-c:a", "libopus", "-b:a", "160k"]
    if target == ".aac":
        return ["-vn", "-c:a", "aac", "-b:a", "192k"]
    if target == ".m4a":
        return ["-vn", "-c:a", "aac", "-b:a", "192k"]
    if target == ".wma":
        return ["-vn", "-c:a", "wmav2", "-b:a", "192k"]
    if target == ".aiff":
        return ["-vn", "-c:a", "pcm_s16be"]
    if target == ".mp4":
        return [
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
        ]
    if target in {".mkv", ".mov"}:
        return [
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
        ]
    if target == ".webm":
        return [
            "-c:v",
            "libvpx-vp9",
            "-crf",
            "31",
            "-b:v",
            "0",
            "-c:a",
            "libopus",
            "-b:a",
            "128k",
        ]
    if target == ".avi":
        return ["-c:v", "mpeg4", "-q:v", "4", "-c:a", "libmp3lame", "-q:a", "3"]
    if target == ".m4v":
        return ["-an", "-c:v", "libx264", "-preset", "medium", "-crf", "20"]
    if target == ".flv":
        return ["-c:v", "flv", "-q:v", "5", "-c:a", "libmp3lame", "-b:a", "160k"]
    if target == ".mpeg":
        return ["-c:v", "mpeg2video", "-q:v", "4", "-c:a", "mp2", "-b:a", "192k"]
    if target == ".3gp":
        return ["-c:v", "libx264", "-profile:v", "baseline", "-level", "3.0", "-c:a", "aac", "-b:a", "128k"]
    if target == ".ogv":
        return ["-c:v", "libtheora", "-q:v", "7", "-c:a", "libvorbis", "-q:a", "5"]
    if target == ".ts":
        return ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-c:a", "aac", "-b:a", "192k"]
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
    LOGGER.debug("Executing FFmpeg command: %s", " ".join(command))
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
        LOGGER.error("FFmpeg failed with code %s: %s", completed.returncode, completed.stderr.strip())
        raise ExternalToolError(f"Media conversion failed: {concise}")
