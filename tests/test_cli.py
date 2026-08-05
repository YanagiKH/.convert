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


def test_cli_debug_mode_reports_log_file(tmp_path: Path, monkeypatch, capsys) -> None:
    source = tmp_path / "note.txt"
    destination = tmp_path / "note.html"
    log_path = tmp_path / "run.log"
    source.write_text("debug conversion", encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "dotconvert",
            str(source),
            str(destination),
            "--yes",
            "--debug",
            "--log-file",
            str(log_path),
        ],
    )

    assert main() == 0
    assert log_path.exists()
    assert "debug log:" in capsys.readouterr().err


def test_cli_lists_formats(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["dotconvert", "--list-formats"])
    assert main() == 0
    output = capsys.readouterr().out
    assert ".tar.xz" in output
    assert ".jsonl" in output
