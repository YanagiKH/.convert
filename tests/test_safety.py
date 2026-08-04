from pathlib import Path

import pytest
from PIL import Image

from dotconvert.engine import ConversionEngine
from dotconvert.errors import DotConvertError
from dotconvert.models import ConversionMode, ConversionPlan


def test_existing_destination_requires_explicit_overwrite(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    destination = tmp_path / "destination.jpg"
    Image.new("RGB", (4, 4), "red").save(source)
    destination.write_bytes(b"original destination")

    with pytest.raises(DotConvertError, match="destination already exists"):
        ConversionEngine().convert(
            ConversionPlan(source=source, target_extension=".jpg", destination=destination)
        )
    assert destination.read_bytes() == b"original destination"


def test_failed_conversion_does_not_modify_existing_destination(tmp_path: Path) -> None:
    source = tmp_path / "broken.png"
    destination = tmp_path / "destination.jpg"
    source.write_bytes(b"not an image")
    destination.write_bytes(b"keep me")

    with pytest.raises(DotConvertError, match="Image conversion failed"):
        ConversionEngine().convert(
            ConversionPlan(
                source=source,
                target_extension=".jpg",
                destination=destination,
                overwrite_existing=True,
            )
        )
    assert destination.read_bytes() == b"keep me"
    assert source.read_bytes() == b"not an image"


def test_replace_mode_reports_danger_warning(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    destination = tmp_path / "destination.jpg"
    Image.new("RGB", (4, 4), "red").save(source)
    warnings = ConversionEngine().warnings_for(
        ConversionPlan(
            source=source,
            target_extension=".jpg",
            destination=destination,
            mode=ConversionMode.REPLACE_SOURCE,
        )
    )
    assert any(item.code == "replace-source" for item in warnings)
