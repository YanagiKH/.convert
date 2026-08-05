from __future__ import annotations

import logging
import os
import queue
from logging.handlers import RotatingFileHandler
from pathlib import Path

APP_LOGGER_NAME = "dotconvert"


class QueueLogHandler(logging.Handler):
    def __init__(self, output: queue.Queue[str]) -> None:
        super().__init__()
        self.output = output

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.output.put_nowait(self.format(record))
        except Exception:
            self.handleError(record)


def default_log_path() -> Path:
    if os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return root / "dotconvert" / "logs" / "dotconvert.log"
    state_home = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return state_home / "dotconvert" / "dotconvert.log"


def configure_logging(
    *,
    debug: bool = False,
    log_path: Path | None = None,
    output_queue: queue.Queue[str] | None = None,
) -> Path:
    destination = (log_path or default_log_path()).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(APP_LOGGER_NAME)
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.propagate = False
    for handler in tuple(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(threadName)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = RotatingFileHandler(
        destination,
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if output_queue is not None:
        queue_handler = QueueLogHandler(output_queue)
        queue_handler.setLevel(logging.DEBUG if debug else logging.INFO)
        queue_handler.setFormatter(formatter)
        logger.addHandler(queue_handler)

    logger.info("Logging initialized (debug=%s, file=%s)", debug, destination)
    return destination
