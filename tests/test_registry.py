from pathlib import Path

from dotconvert.registry import (
    FormatFamily,
    available_targets,
    extension_for_path,
    family_for_extension,
    normalize_extension,
)


def test_multi_suffix_and_aliases() -> None:
    assert extension_for_path(Path("backup.TAR.GZ")) == ".tar.gz"
    assert extension_for_path(Path("backup.TBZ2")) == ".tar.bz2"
    assert extension_for_path(Path("backup.TXZ")) == ".tar.xz"
    assert normalize_extension("jpeg") == ".jpg"
    assert normalize_extension("dib") == ".bmp"
    assert normalize_extension("mpg") == ".mpeg"
    assert family_for_extension(".toml") == FormatFamily.DATA


def test_new_targets_are_exposed_without_duplicate_aliases() -> None:
    image_targets = available_targets(Path("input.png"))
    assert ".tga" in image_targets
    assert ".pgm" in image_targets
    assert image_targets.count(".jpg") == 1

    archive_targets = available_targets(Path("input.zip"))
    assert ".tar.bz2" in archive_targets
    assert ".tar.xz" in archive_targets
