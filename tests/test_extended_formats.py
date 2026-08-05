import json
import tarfile
import zipfile
from pathlib import Path

from PIL import Image

from dotconvert.engine import ConversionEngine
from dotconvert.models import ConversionPlan


def convert(source: Path, destination: Path) -> None:
    ConversionEngine().convert(
        ConversionPlan(
            source=source,
            target_extension="".join(destination.suffixes[-2:])
            if destination.name.endswith((".tar.bz2", ".tar.xz"))
            else destination.suffix,
            destination=destination,
        )
    )


def test_extended_image_targets(tmp_path: Path) -> None:
    source = tmp_path / "source.png"
    Image.new("RGBA", (8, 6), (1, 2, 3, 120)).save(source)

    for extension in (".tga", ".pcx", ".ppm", ".pgm", ".pbm"):
        destination = tmp_path / f"output{extension}"
        convert(source, destination)
        with Image.open(destination) as converted:
            assert converted.size == (8, 6)


def test_jsonl_tsv_and_toml_round_trip(tmp_path: Path) -> None:
    source = tmp_path / "records.jsonl"
    source.write_text('{"name":"Miku","score":39}\n{"name":"Rin","score":2}\n', encoding="utf-8")
    tsv = tmp_path / "records.tsv"
    convert(source, tsv)
    assert "name\tscore" in tsv.read_text(encoding="utf-8-sig")

    json_output = tmp_path / "records.json"
    convert(tsv, json_output)
    assert json.loads(json_output.read_text(encoding="utf-8"))[0]["name"] == "Miku"

    config = tmp_path / "config.json"
    config.write_text('{"app":{"language":"en","debug":true},"quality":92}', encoding="utf-8")
    toml_output = tmp_path / "config.toml"
    convert(config, toml_output)
    assert '["app"]' in toml_output.read_text(encoding="utf-8")


def test_bzip2_and_xz_tar_repacking(tmp_path: Path) -> None:
    source = tmp_path / "input.zip"
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("folder/file.txt", "safe")

    for suffix in (".tar.bz2", ".tar.xz"):
        destination = tmp_path / f"output{suffix}"
        convert(source, destination)
        with tarfile.open(destination, "r:*") as archive:
            assert archive.extractfile("folder/file.txt").read() == b"safe"
