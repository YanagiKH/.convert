import csv
import json
from pathlib import Path

import pytest

from dotconvert.engine import ConversionEngine
from dotconvert.errors import DotConvertError
from dotconvert.models import ConversionPlan


def test_markdown_to_html(tmp_path: Path) -> None:
    source = tmp_path / "note.md"
    destination = tmp_path / "note.html"
    source.write_text("# Title\n\n- one\n- two\n", encoding="utf-8")

    ConversionEngine().convert(
        ConversionPlan(source=source, target_extension=".html", destination=destination)
    )

    value = destination.read_text(encoding="utf-8")
    assert "<h1>Title</h1>" in value
    assert "<li>one</li>" in value


def test_json_to_csv_flat_rows(tmp_path: Path) -> None:
    source = tmp_path / "rows.json"
    destination = tmp_path / "rows.csv"
    source.write_text(json.dumps([{"name": "Miku", "score": 39}, {"name": "Rin", "score": 27}]), encoding="utf-8")

    ConversionEngine().convert(
        ConversionPlan(source=source, target_extension=".csv", destination=destination)
    )

    with destination.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows == [{"name": "Miku", "score": "39"}, {"name": "Rin", "score": "27"}]


def test_nested_json_to_csv_is_blocked_without_overwriting(tmp_path: Path) -> None:
    source = tmp_path / "nested.json"
    destination = tmp_path / "nested.csv"
    source.write_text('{"name": "Miku", "nested": {"value": 1}}', encoding="utf-8")
    destination.write_text("keep", encoding="utf-8")

    with pytest.raises(DotConvertError, match="Nested data"):
        ConversionEngine().convert(
            ConversionPlan(
                source=source,
                target_extension=".csv",
                destination=destination,
                overwrite_existing=True,
            )
        )

    assert destination.read_text(encoding="utf-8") == "keep"


def test_yaml_json_round_trip(tmp_path: Path) -> None:
    source = tmp_path / "config.yaml"
    json_output = tmp_path / "config.json"
    yaml_output = tmp_path / "config-again.yaml"
    source.write_text("name: .convert\nformats:\n  - png\n  - json\n", encoding="utf-8")

    engine = ConversionEngine()
    engine.convert(ConversionPlan(source=source, target_extension=".json", destination=json_output))
    engine.convert(ConversionPlan(source=json_output, target_extension=".yaml", destination=yaml_output))

    assert json.loads(json_output.read_text(encoding="utf-8"))["name"] == ".convert"
    assert "formats:" in yaml_output.read_text(encoding="utf-8")
