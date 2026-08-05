import logging
import queue
from pathlib import Path

from dotconvert.debug import configure_logging


def test_debug_logging_writes_file_and_ui_queue(tmp_path: Path) -> None:
    output: queue.Queue[str] = queue.Queue()
    log_path = configure_logging(
        debug=True,
        log_path=tmp_path / "debug.log",
        output_queue=output,
    )
    logging.getLogger("dotconvert.test").debug("conversion detail")
    for handler in logging.getLogger("dotconvert").handlers:
        handler.flush()

    assert log_path.exists()
    assert "conversion detail" in log_path.read_text(encoding="utf-8")
    queued = [output.get(timeout=1), output.get(timeout=1)]
    assert any("conversion detail" in line for line in queued)
