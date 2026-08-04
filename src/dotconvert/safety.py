from __future__ import annotations

import os
import shutil
from pathlib import Path

from .errors import DotConvertError
from .models import ConversionMode, ConversionPlan, ConversionWarning, Severity
from .registry import FormatFamily, extension_for_path, family_for_extension, normalize_extension


LOSSY_IMAGE = {".jpg", ".webp", ".gif"}
LOSSY_AUDIO = {".mp3", ".ogg", ".aac", ".m4a"}
LOSSY_VIDEO = {".mp4", ".webm", ".avi", ".mov"}


def resolve_destination(plan: ConversionPlan) -> Path:
    source = plan.source.expanduser().resolve()
    extension = normalize_extension(plan.target_extension)
    if plan.destination is not None:
        destination = plan.destination.expanduser().resolve()
        if not destination.name.lower().endswith(extension):
            destination = destination.with_name(destination.name + extension)
        return destination
    base_name = source.name
    source_extension = extension_for_path(source)
    stem = base_name[: -len(source_extension)]
    return source.with_name(stem + extension)


def validate_plan(plan: ConversionPlan) -> tuple[Path, Path]:
    source = plan.source.expanduser().resolve()
    if not source.exists() or not source.is_file():
        raise DotConvertError("The selected source file no longer exists.")
    if not os.access(source, os.R_OK):
        raise DotConvertError("The selected source file is not readable.")
    if not 1 <= plan.image_quality <= 100:
        raise DotConvertError("Image quality must be between 1 and 100.")

    source_extension = extension_for_path(source)
    target_extension = normalize_extension(plan.target_extension)
    if family_for_extension(source_extension) != family_for_extension(target_extension):
        raise DotConvertError("Source and target formats belong to incompatible format groups.")

    destination = resolve_destination(plan)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if source == destination and source_extension == target_extension:
        raise DotConvertError("Source and destination are identical; choose a different format or path.")
    if destination.exists() and not plan.overwrite_existing:
        raise DotConvertError("The destination already exists. Enable overwrite or choose another path.")
    if not os.access(destination.parent, os.W_OK):
        raise DotConvertError("The destination folder is not writable.")

    required = max(source.stat().st_size * 2, 16 * 1024 * 1024)
    free = shutil.disk_usage(destination.parent).free
    if free < required:
        raise DotConvertError("There may not be enough free disk space to complete the conversion safely.")
    return source, destination


def assess_risks(plan: ConversionPlan) -> tuple[ConversionWarning, ...]:
    source_extension = extension_for_path(plan.source)
    target_extension = normalize_extension(plan.target_extension)
    family = family_for_extension(source_extension)
    warnings: list[ConversionWarning] = []

    if source_extension == target_extension:
        warnings.append(ConversionWarning("same-format", "The file will be re-encoded in the same format."))

    if family == FormatFamily.IMAGE:
        if target_extension in LOSSY_IMAGE:
            warnings.append(ConversionWarning("lossy-image", "The selected image format can reduce quality."))
        if target_extension == ".jpg" and source_extension in {".png", ".webp", ".gif", ".tiff", ".ico"}:
            warnings.append(ConversionWarning("alpha-loss", "JPEG cannot preserve transparency; transparent areas will become white."))
        if source_extension in {".gif", ".webp", ".tiff"} and target_extension not in {".gif", ".webp", ".tiff"}:
            warnings.append(ConversionWarning("animation-loss", "Animated or multi-page image content may be reduced to the first frame."))
        if target_extension == ".gif":
            warnings.append(ConversionWarning("palette-loss", "GIF uses a limited color palette and may reduce color detail."))

    elif family == FormatFamily.TEXT:
        if target_extension == ".txt":
            warnings.append(ConversionWarning("formatting-loss", "Plain text cannot preserve rich formatting, links, or embedded media."))
        elif source_extension == ".html" and target_extension == ".md":
            warnings.append(ConversionWarning("html-to-markdown", "Complex HTML layout and styling cannot be preserved exactly."))

    elif family == FormatFamily.DATA:
        if target_extension == ".csv":
            warnings.append(ConversionWarning("tabular-only", "CSV only preserves a flat table; nested data cannot be converted safely."))
        if source_extension == ".xml" or target_extension == ".xml":
            warnings.append(ConversionWarning("xml-shape", "XML attributes and mixed text may be represented differently after conversion."))

    elif family == FormatFamily.ARCHIVE:
        warnings.append(ConversionWarning("archive-metadata", "Repacking may change compression, timestamps, permissions, or archive comments."))

    elif family == FormatFamily.MEDIA:
        if target_extension in LOSSY_AUDIO | LOSSY_VIDEO:
            warnings.append(ConversionWarning("lossy-media", "The selected media format uses lossy encoding and may reduce quality."))
        warnings.append(ConversionWarning("media-streams", "Unsupported subtitle, attachment, chapter, or metadata streams may not be preserved."))

    if plan.mode == ConversionMode.REPLACE_SOURCE:
        warnings.append(
            ConversionWarning(
                "replace-source",
                "After a successful conversion, the original file will be moved to the system recycle bin.",
                Severity.DANGER,
            )
        )
    if plan.overwrite_existing:
        warnings.append(
            ConversionWarning(
                "overwrite-existing",
                "An existing destination file will be replaced only after conversion succeeds.",
                Severity.DANGER,
            )
        )
    return tuple(warnings)
