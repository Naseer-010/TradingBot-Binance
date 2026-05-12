"""
Logging Configuration
=====================

Configures dual-output logging:
  • Console  → Rich-formatted, INFO+ level, coloured & styled
  • File     → Plain text with full timestamps, DEBUG+ level, rotating

All API requests, responses, and errors are logged to `logs/trading_bot.log`.
"""

import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from rich.logging import RichHandler


def setup_logging(log_dir: str = "logs", log_level: str = "DEBUG") -> logging.Logger:
    """
    Initialise and return the application-wide logger.

    Args:
        log_dir:   Directory to store log files (created if missing).
        log_level: Minimum level for the *file* handler (console is always INFO).

    Returns:
        Configured root logger instance.
    """
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Timestamped log file for this session
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_path / f"trading_bot_{timestamp}.log"

    # Also maintain a "latest" symlink / fixed-name file
    latest_log = log_path / "trading_bot.log"

    logger = logging.getLogger("trading_bot")
    logger.setLevel(getattr(logging, log_level.upper(), logging.DEBUG))

    # Prevent duplicate handlers on re-init
    if logger.handlers:
        logger.handlers.clear()

    # ── File handler (rotating, plain text) ──────────────────────────
    file_fmt = logging.Formatter(
        fmt="%(asctime)s │ %(levelname)-8s │ %(name)-20s │ %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = RotatingFileHandler(
        str(log_file),
        maxBytes=5 * 1024 * 1024,  # 5 MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_fmt)
    logger.addHandler(file_handler)

    # Also log to the "latest" fixed file
    latest_handler = logging.FileHandler(str(latest_log), mode="w", encoding="utf-8")
    latest_handler.setLevel(logging.DEBUG)
    latest_handler.setFormatter(file_fmt)
    logger.addHandler(latest_handler)

    # ── Console handler (Rich, styled) ───────────────────────────────
    console_handler = RichHandler(
        level=logging.INFO,
        rich_tracebacks=True,
        tracebacks_show_locals=True,
        show_time=True,
        show_path=False,
        markup=True,
    )
    console_handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(console_handler)

    logger.info(f"Logging initialised → {log_file}")
    return logger
