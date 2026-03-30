"""
Logging Configuration

Provides structured JSON logging configuration for the application.
"""

import logging
import sys
from typing import Any

from app.core.config import settings


def get_logging_config() -> dict[str, Any]:
    """
    Get logging configuration based on environment.

    Returns:
        Dictionary with logging configuration for dictConfig.
    """
    # Use JSON format in production, simple format in development
    if settings.ENVIRONMENT == "production":
        formatters = {
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s",
            }
        }
        default_formatter = "json"
    else:
        formatters = {
            "simple": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            }
        }
        default_formatter = "simple"

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": formatters,
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": default_formatter,
            },
        },
        "loggers": {
            "app": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
        },
        "root": {
            "level": "INFO",
            "handlers": ["console"],
        },
    }


def setup_logging() -> None:
    """Setup application logging."""
    import logging.config

    config = get_logging_config()
    logging.config.dictConfig(config)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.

    Args:
        name: Logger name, typically __name__.

    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)
