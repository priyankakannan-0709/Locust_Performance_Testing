import logging
from pathlib import Path


_logger: logging.Logger | None = None


def setup_logger(report_dir: Path) -> logging.Logger:
    """
    Initialise the framework logger.
    Must be called ONCE from run_performance.py immediately after
    report_dir is created — before any other module is used.

    Args:
        report_dir: timestamped report directory — run.log written here

    Returns:
        Configured root framework logger
    """
    global _logger

    log_format  = "%(asctime)s | %(levelname)-8s | %(name)-40s | %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    formatter   = logging.Formatter(log_format, datefmt=date_format)

    logger = logging.getLogger("performance_framework")
    logger.setLevel(logging.DEBUG)

    # ── Avoid duplicate handlers if called more than once ──────────────────
    if logger.handlers:
        return logger

    # ── Console handler — INFO and above ──────────────────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # ── File handler — DEBUG and above ────────────────────────────────────
    log_path     = report_dir / "run.log"
    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # ── Capture Locust logs into same run.log ──────────────────────────────
    locust_logger = logging.getLogger("locust")
    locust_logger.addHandler(file_handler)

    _logger = logger
    logger.info(f"Logger initialised — log file: {log_path}")
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a child logger for a specific module.
    Call once at module level in each file.

    Args:
        name: pass __name__ — becomes performance_framework.<module>

    Returns:
        Child logger inheriting parent handlers

    Usage:
        from utils.logger import get_logger
        logger = get_logger(__name__)
    """
    return logging.getLogger(f"performance_framework.{name}")