from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from .errors import UnsupportedFormatError


class FormatFamily(str, Enum):
    IMAGE = "image"
    TEXT = "text"
    DATA = "data"
    ARCHIVE = "archive"
    MEDIA = "media"


@dataclass(frozen=True)
class FormatInfo:
    extension: str
    label: str
    family: FormatFamily


_FORMATS = (
    FormatInfo(".png", "PNG image", FormatFamily.IMAGE),
    FormatInfo(".jpg", "JPEG image", FormatFamily.IMAGE),
    FormatInfo(".jpeg", "JPEG image", FormatFamily.IMAGE),
    FormatInfo(".webp", "WebP image", FormatFamily.IMAGE),
    FormatInfo(".bmp", "BMP image", FormatFamily.IMAGE),
    FormatInfo(".tif", "TIFF image", FormatFamily.IMAGE),
    FormatInfo(".tiff", "TIFF image", FormatFamily.IMAGE),
    FormatInfo(".gif", "GIF image", FormatFamily.IMAGE),
    FormatInfo(".ico", "Windows icon", FormatFamily.IMAGE),
    FormatInfo(".txt", "Plain text", FormatFamily.TEXT),
    FormatInfo(".md", "Markdown", FormatFamily.TEXT),
    FormatInfo(".markdown", "Markdown", FormatFamily.TEXT),
    FormatInfo(".html", "HTML document", FormatFamily.TEXT),
    FormatInfo(".htm", "HTML document", FormatFamily.TEXT),
    FormatInfo(".json", "JSON data", FormatFamily.DATA),
    FormatInfo(".yaml", "YAML data", FormatFamily.DATA),
    FormatInfo(".yml", "YAML data", FormatFamily.DATA),
    FormatInfo(".csv", "CSV table", FormatFamily.DATA),
    FormatInfo(".xml", "XML data", FormatFamily.DATA),
    FormatInfo(".zip", "ZIP archive", FormatFamily.ARCHIVE),
    FormatInfo(".tar", "TAR archive", FormatFamily.ARCHIVE),
    FormatInfo(".tar.gz", "Compressed TAR archive", FormatFamily.ARCHIVE),
    FormatInfo(".tgz", "Compressed TAR archive", FormatFamily.ARCHIVE),
    FormatInfo(".mp3", "MP3 audio", FormatFamily.MEDIA),
    FormatInfo(".wav", "WAV audio", FormatFamily.MEDIA),
    FormatInfo(".flac", "FLAC audio", FormatFamily.MEDIA),
    FormatInfo(".ogg", "Ogg audio", FormatFamily.MEDIA),
    FormatInfo(".aac", "AAC audio", FormatFamily.MEDIA),
    FormatInfo(".m4a", "M4A audio", FormatFamily.MEDIA),
    FormatInfo(".mp4", "MP4 video", FormatFamily.MEDIA),
    FormatInfo(".mkv", "Matroska video", FormatFamily.MEDIA),
    FormatInfo(".webm", "WebM video", FormatFamily.MEDIA),
    FormatInfo(".mov", "QuickTime video", FormatFamily.MEDIA),
    FormatInfo(".avi", "AVI video", FormatFamily.MEDIA),
)

FORMAT_BY_EXTENSION = {item.extension: item for item in _FORMATS}
FAMILY_TARGETS: dict[FormatFamily, tuple[str, ...]] = {
    family: tuple(item.extension for item in _FORMATS if item.family == family)
    for family in FormatFamily
}


def normalize_extension(value: str) -> str:
    value = value.strip().lower()
    if not value.startswith("."):
        value = f".{value}"
    aliases = {".jpeg": ".jpg", ".tif": ".tiff", ".htm": ".html", ".markdown": ".md", ".tgz": ".tar.gz", ".yml": ".yaml"}
    return aliases.get(value, value)


def extension_for_path(path: Path) -> str:
    lower = path.name.lower()
    for extension in sorted(FORMAT_BY_EXTENSION, key=len, reverse=True):
        if lower.endswith(extension):
            return normalize_extension(extension)
    raise UnsupportedFormatError(f"Unsupported source format: {path.suffix or '(no extension)'}")


def family_for_extension(extension: str) -> FormatFamily:
    normalized = normalize_extension(extension)
    item = FORMAT_BY_EXTENSION.get(normalized)
    if item is None:
        raise UnsupportedFormatError(f"Unsupported target format: {extension}")
    return item.family


def available_targets(path: Path, ffmpeg_available: bool = True) -> tuple[str, ...]:
    family = family_for_extension(extension_for_path(path))
    targets = tuple(dict.fromkeys(normalize_extension(item) for item in FAMILY_TARGETS[family]))
    if family == FormatFamily.MEDIA and not ffmpeg_available:
        return ()
    return targets


def display_label(extension: str) -> str:
    normalized = normalize_extension(extension)
    info = FORMAT_BY_EXTENSION.get(normalized)
    return f"{normalized.upper()} — {info.label}" if info else normalized.upper()
