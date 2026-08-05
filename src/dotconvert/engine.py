from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

from send2trash import send2trash

from .converters import (
    convert_archive,
    convert_data,
    convert_image,
    convert_media,
    convert_text,
    find_ffmpeg,
)
from .errors import DotConvertError
from .models import ConversionMode, ConversionPlan, ConversionResult, ConversionWarning, Severity
from .registry import (
    FormatFamily,
    available_targets,
    extension_for_path,
    family_for_extension,
    normalize_extension,
)
from .safety import assess_risks, validate_plan

LOGGER = logging.getLogger("dotconvert.engine")


class ConversionEngine:
    """Validate and perform conversions using temporary files and atomic replacement."""

    def ffmpeg_available(self) -> bool:
        available = find_ffmpeg() is not None
        LOGGER.debug("FFmpeg available: %s", available)
        return available

    def targets_for(self, source: Path) -> tuple[str, ...]:
        targets = available_targets(source, ffmpeg_available=self.ffmpeg_available())
        LOGGER.debug("Targets for %s: %s", source, targets)
        return targets

    def warnings_for(self, plan: ConversionPlan) -> tuple[ConversionWarning, ...]:
        validate_plan(plan)
        warnings = assess_risks(plan)
        LOGGER.debug("Warnings for %s -> %s: %s", plan.source, plan.target_extension, warnings)
        return warnings

    def convert(self, plan: ConversionPlan) -> ConversionResult:
        source, destination = validate_plan(plan)
        warnings = list(assess_risks(plan))
        target = normalize_extension(plan.target_extension)
        family = family_for_extension(extension_for_path(source))
        LOGGER.info("Starting conversion: %s -> %s (%s)", source, destination, family.value)

        temporary_path: Path | None = None
        try:
            file_descriptor, temporary_name = tempfile.mkstemp(
                prefix=f".{destination.stem}.dotconvert-",
                suffix=target,
                dir=destination.parent,
            )
            os.close(file_descriptor)
            temporary_path = Path(temporary_name)
            temporary_path.unlink(missing_ok=True)
            LOGGER.debug("Temporary output path: %s", temporary_path)

            if family == FormatFamily.IMAGE:
                convert_image(source, temporary_path, target, plan.image_quality)
            elif family == FormatFamily.TEXT:
                convert_text(source, temporary_path, target)
            elif family == FormatFamily.DATA:
                convert_data(source, temporary_path, target)
            elif family == FormatFamily.ARCHIVE:
                convert_archive(source, temporary_path, target)
            elif family == FormatFamily.MEDIA:
                convert_media(source, temporary_path, target)
            else:  # pragma: no cover - enum is exhaustive
                raise DotConvertError("No converter is available for this format group.")

            if not temporary_path.exists() or temporary_path.stat().st_size == 0:
                raise DotConvertError(
                    "Conversion produced an empty output file; the original was not changed."
                )

            os.replace(temporary_path, destination)
            temporary_path = None
            LOGGER.info("Conversion committed atomically: %s", destination)

            source_recycled = False
            if plan.mode == ConversionMode.REPLACE_SOURCE and source != destination:
                try:
                    send2trash(str(source))
                    source_recycled = True
                    LOGGER.info("Source moved to recycle bin: %s", source)
                except OSError as exc:
                    LOGGER.exception("Unable to recycle source: %s", source)
                    warnings.append(
                        ConversionWarning(
                            "recycle-failed",
                            "The converted file was saved, but the original could not be moved "
                            f"to the recycle bin: {exc}",
                            Severity.WARNING,
                        )
                    )
            return ConversionResult(
                source=source,
                destination=destination,
                warnings=tuple(warnings),
                source_recycled=source_recycled,
            )
        except Exception:
            LOGGER.exception("Conversion failed: %s -> %s", source, destination)
            raise
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
                LOGGER.debug("Removed temporary output: %s", temporary_path)
