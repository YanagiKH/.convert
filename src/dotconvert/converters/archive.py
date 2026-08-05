from __future__ import annotations

import shutil
import stat
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import Iterator

from ..errors import DotConvertError, UnsafeArchiveError
from ..registry import extension_for_path, normalize_extension

MAX_UNCOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024
MAX_ENTRY_COUNT = 100_000
MAX_COMPRESSION_RATIO = 500


def _safe_destination(root: Path, member_name: str) -> Path:
    candidate = (root / member_name).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as exc:
        raise UnsafeArchiveError(f"Unsafe archive path detected: {member_name}") from exc
    return candidate


def _extract_zip(source: Path, root: Path) -> None:
    with zipfile.ZipFile(source) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_ENTRY_COUNT:
            raise UnsafeArchiveError("Archive contains too many entries.")
        total = sum(info.file_size for info in infos)
        if total > MAX_UNCOMPRESSED_BYTES:
            raise UnsafeArchiveError("Archive expands beyond the configured 2 GiB safety limit.")
        for info in infos:
            if info.flag_bits & 0x1:
                raise UnsafeArchiveError("Encrypted ZIP archives are not supported.")
            mode = info.external_attr >> 16
            if stat.S_ISLNK(mode):
                raise UnsafeArchiveError("Symbolic links inside ZIP archives are not supported.")
            if info.compress_size and info.file_size / info.compress_size > MAX_COMPRESSION_RATIO:
                raise UnsafeArchiveError("Suspicious compression ratio detected; extraction was blocked.")
            target = _safe_destination(root, info.filename)
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(info) as input_handle, target.open("wb") as output_handle:
                shutil.copyfileobj(input_handle, output_handle, length=1024 * 1024)


def _extract_tar(source: Path, root: Path) -> None:
    with tarfile.open(source, mode="r:*") as archive:
        members = archive.getmembers()
        if len(members) > MAX_ENTRY_COUNT:
            raise UnsafeArchiveError("Archive contains too many entries.")
        total = sum(member.size for member in members if member.isfile())
        if total > MAX_UNCOMPRESSED_BYTES:
            raise UnsafeArchiveError("Archive expands beyond the configured 2 GiB safety limit.")
        for member in members:
            if member.issym() or member.islnk() or member.isdev():
                raise UnsafeArchiveError("Links and device files inside TAR archives are not supported.")
            target = _safe_destination(root, member.name)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                extracted = archive.extractfile(member)
                if extracted is None:
                    raise UnsafeArchiveError(f"Unable to read archive entry: {member.name}")
                with extracted, target.open("wb") as output_handle:
                    shutil.copyfileobj(extracted, output_handle, length=1024 * 1024)


def _iter_files(root: Path) -> Iterator[tuple[Path, Path]]:
    for path in sorted(root.rglob("*")):
        yield path, path.relative_to(root)


def _write_zip(root: Path, destination: Path) -> None:
    with zipfile.ZipFile(
        destination,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=6,
    ) as archive:
        for path, relative in _iter_files(root):
            if path.is_dir():
                archive.writestr(relative.as_posix().rstrip("/") + "/", b"")
            elif path.is_file():
                archive.write(path, relative.as_posix())


def _write_tar(root: Path, destination: Path, target: str) -> None:
    modes = {
        ".tar": "w",
        ".tar.gz": "w:gz",
        ".tar.bz2": "w:bz2",
        ".tar.xz": "w:xz",
    }
    with tarfile.open(destination, mode=modes[target], format=tarfile.PAX_FORMAT) as archive:
        for path, relative in _iter_files(root):
            archive.add(path, arcname=relative.as_posix(), recursive=False)


def convert_archive(source: Path, destination: Path, target_extension: str) -> None:
    source_extension = extension_for_path(source)
    target = normalize_extension(target_extension)
    try:
        with tempfile.TemporaryDirectory(prefix="dotconvert-archive-") as temporary:
            root = Path(temporary)
            if source_extension == ".zip":
                _extract_zip(source, root)
            else:
                _extract_tar(source, root)
            if target == ".zip":
                _write_zip(root, destination)
            elif target in {".tar", ".tar.gz", ".tar.bz2", ".tar.xz"}:
                _write_tar(root, destination, target)
            else:
                raise DotConvertError(f"Unsupported archive target: {target}")
    except DotConvertError:
        raise
    except (OSError, zipfile.BadZipFile, tarfile.TarError) as exc:
        raise DotConvertError(f"Archive conversion failed: {exc}") from exc
