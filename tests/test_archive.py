import io
import tarfile
import zipfile
from pathlib import Path

import pytest

from dotconvert.engine import ConversionEngine
from dotconvert.errors import UnsafeArchiveError
from dotconvert.models import ConversionPlan


def test_zip_to_tar_gz_preserves_files(tmp_path: Path) -> None:
    source = tmp_path / "source.zip"
    destination = tmp_path / "converted.tar.gz"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("folder/hello.txt", "hello")

    ConversionEngine().convert(
        ConversionPlan(source=source, target_extension=".tar.gz", destination=destination)
    )

    with tarfile.open(destination, "r:gz") as archive:
        assert archive.extractfile("folder/hello.txt").read() == b"hello"  # type: ignore[union-attr]


def test_tar_path_traversal_is_blocked(tmp_path: Path) -> None:
    source = tmp_path / "unsafe.tar"
    destination = tmp_path / "unsafe.zip"
    with tarfile.open(source, "w") as archive:
        info = tarfile.TarInfo("../escape.txt")
        payload = b"blocked"
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))

    with pytest.raises(UnsafeArchiveError, match="Unsafe archive path"):
        ConversionEngine().convert(
            ConversionPlan(source=source, target_extension=".zip", destination=destination)
        )
    assert not destination.exists()
