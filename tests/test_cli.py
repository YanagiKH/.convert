import sys
from pathlib import Path

from dotconvert.__main__ import main


def test_cli_converts_text_file(tmp_path: Path, monkeypatch, capsys) -> None:
    source = tmp_path / "note.txt"
    destination = tmp_path / "note.html"
    source.write_text("safe conversion", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["dotconvert", str(source), str(destination), "--yes"])

    assert main() == 0
    assert destination.exists()
    assert "safe conversion" in destination.read_text(encoding="utf-8")
    assert str(destination) in capsys.readouterr().out


def test_cli_requires_destination(monkeypatch, capsys, tmp_path: Path) -> None:
    source = tmp_path / "note.txt"
    source.write_text("content", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["dotconvert", str(source)])

    assert main() == 2
    assert "destination is required" in capsys.readouterr().err
