"""
app/utils/logger.py
===================
Centralised, reusable logging factory.

Logs go to both the console and a rotating file for later inspection. A small
guard prevents attaching handlers twice when modules are re-imported.

SOLID note (Single Responsibility): this module only configures logging.
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from app.config import LOG_DIR

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured: set[str] = set()


def get_logger(name: str) -> logging.Logger:
    """Return a configured logger for the given module name."""
    logger = logging.getLogger(name)
    if name in _configured:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    file_handler = RotatingFileHandler(
        LOG_DIR / "app.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    _configured.add(name)
    return logger
