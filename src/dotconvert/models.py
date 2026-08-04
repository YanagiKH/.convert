from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class ConversionMode(str, Enum):
    SAVE_AS = "save_as"
    REPLACE_SOURCE = "replace_source"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    DANGER = "danger"


@dataclass(frozen=True)
class ConversionWarning:
    code: str
    message: str
    severity: Severity = Severity.WARNING


@dataclass(frozen=True)
class ConversionPlan:
    source: Path
    target_extension: str
    destination: Path | None = None
    mode: ConversionMode = ConversionMode.SAVE_AS
    overwrite_existing: bool = False
    image_quality: int = 92

    def normalized_extension(self) -> str:
        extension = self.target_extension.strip().lower()
        if not extension.startswith("."):
            extension = f".{extension}"
        return extension


@dataclass(frozen=True)
class ConversionResult:
    source: Path
    destination: Path
    warnings: tuple[ConversionWarning, ...] = field(default_factory=tuple)
    source_recycled: bool = False
