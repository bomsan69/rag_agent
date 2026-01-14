"""Helper utilities."""

import logging
from pathlib import Path
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler
import sys


def setup_logging(log_level: str = "INFO", log_dir: str = "./logs"):
    """Set up logging configuration with daily log files.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_dir: Directory to store log files (default: ./logs)
    """
    # Ensure log directory exists
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # Create log filename with current date
    current_date = datetime.now().strftime("%Y-%m-%d")
    log_file = log_path / f"{current_date}_app.log"

    # Create formatter
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Console handler (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler - TimedRotatingFileHandler for daily rotation
    # This will create a new log file at midnight
    file_handler = TimedRotatingFileHandler(
        filename=log_file,
        when="midnight",
        interval=1,
        backupCount=30,  # Keep last 30 days of logs
        encoding="utf-8"
    )
    file_handler.setLevel(getattr(logging, log_level.upper()))
    file_handler.setFormatter(formatter)

    # Custom suffix for rotated files (YYYY-MM-DD format)
    file_handler.suffix = "%Y-%m-%d_app.log"

    root_logger.addHandler(file_handler)

    root_logger.info(f"Logging initialized - Level: {log_level}, Log file: {log_file}")


def ensure_directory(path: str) -> Path:
    """Ensure directory exists, create if not.

    Args:
        path: Directory path

    Returns:
        Path object
    """
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path
