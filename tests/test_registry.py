from pathlib import Path

from dotconvert.registry import (
    FormatFamily,
    extension_for_path,
    family_for_extension,
    normalize_extension,
)


def test_multi_suffix_and_aliases() -> None:
    assert extension_for_path(Path("backup.TAR.GZ")) == ".tar.gz"
    assert normalize_extension("jpeg") == ".jpg"
    assert normalize_extension("tgz") == ".tar.gz"
    assert family_for_extension(".yaml") == FormatFamily.DATA
