"""Structured logging setup for all apps."""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


def setup_logging(
    app_name: str,
    level: str = "INFO",
    log_file: Optional[str] = None,
    console: bool = True,
) -> logging.Logger:
    """
    Set up structured logging for an app.

    Args:
        app_name: Name of the app (used as logger name)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
        console: Whether to also log to console

    Returns:
        Configured logger instance

    Example:
        logger = setup_logging("drs", level="DEBUG", log_file="logs/drs.log")
        logger.info("DRS app started", extra={"drs_state": "idle"})
    """
    logger = logging.getLogger(app_name)
    logger.setLevel(getattr(logging, level.upper()))

    # Clear any existing handlers
    logger.handlers.clear()

    # Custom formatter with timestamp and context
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # File handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


class RaceLogger:
    """Specialized logger for race events with lap tracking."""

    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.lap_number = 0
        self.lap_start_time: Optional[float] = None

    def start_lap(self):
        """Mark the start of a new lap."""
        self.lap_number += 1
        self.lap_start_time = datetime.now().timestamp()
        self.logger.info(f"Lap {self.lap_number} started")

    def log_event(self, event: str, **kwargs):
        """Log a race event with lap context."""
        extra = {"lap": self.lap_number, **kwargs}
        self.logger.info(event, extra=extra)

    def end_lap(self):
        """Mark the end of a lap and log lap time."""
        if self.lap_start_time:
            lap_time = datetime.now().timestamp() - self.lap_start_time
            self.logger.info(
                f"Lap {self.lap_number} completed",
                extra={"lap": self.lap_number, "lap_time": lap_time},
            )
