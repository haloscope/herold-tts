"""Centralized logging setup for Herold-TTS scripts."""

import logging
import sys
from pathlib import Path

def setup_logger(name: str, level=logging.INFO) -> logging.Logger:
    """Configure logger with console output and optional file logging."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Remove existing handlers to avoid duplication
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    # Format: [LEVEL] script.function — message
    formatter = logging.Formatter(
        fmt='[%(levelname)s] %(name)s — %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger
