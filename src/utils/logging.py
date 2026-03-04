"""Centralised logging configuration."""

import logging
import os
import sys


def _root_level() -> int:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    return getattr(logging, level_name, logging.INFO)


def configure_logging() -> None:
    """Configure the root logger once at startup."""
    logging.basicConfig(
        stream=sys.stdout,
        level=_root_level(),
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def get_logger(name: str) -> logging.Logger:
    """Return a named logger, configuring root logging on first call."""
    if not logging.root.handlers:
        configure_logging()
    return logging.getLogger(name)
