"""Structured logging setup using loguru."""

import sys

from loguru import logger


def _format(record: dict) -> str:
    extra = record["extra"]
    fields = " ".join(f"{k}={v}" for k, v in extra.items()) if extra else ""
    suffix = f"  {fields}" if fields else ""
    return (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> — "
        f"<level>{{message}}</level>{suffix}\n"
    )


def configure_logging(level: str = "INFO", json_logs: bool = False) -> None:
    """Configure loguru for the application.

    Args:
        level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_logs: Emit newline-delimited JSON instead of human-readable text.
    """
    logger.remove()

    if json_logs:
        logger.add(
            sys.stdout,
            level=level,
            serialize=True,
            enqueue=True,
        )
    else:
        logger.add(
            sys.stdout,
            level=level,
            format=_format,
            colorize=True,
            enqueue=True,
        )

    logger.add(
        "logs/legal_radar.log",
        level=level,
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        serialize=json_logs,
        enqueue=True,
    )
