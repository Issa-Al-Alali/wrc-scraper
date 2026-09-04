import logging
import logging.handlers
from pathlib import Path

from pythonjsonlogger import jsonlogger

from common.config import get_settings

_CONFIGURED = False


def setup_logging(logger_name: str = "wrc") -> logging.Logger:
    global _CONFIGURED
    settings = get_settings()
    logger = logging.getLogger(logger_name)

    if _CONFIGURED:
        return logger

    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logger.setLevel(level)

    formatter = jsonlogger.JsonFormatter(
        "%(asctime)s %(name)s %(levelname)s %(message)s"
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    log_dir = Path(settings.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.handlers.RotatingFileHandler(
        log_dir / f"{logger_name}.log", maxBytes=10_000_000, backupCount=5
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    logger.propagate = False
    _CONFIGURED = True
    return logger