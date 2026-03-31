"""
Logging Configuration

Provides structured JSON logging configuration for the application.
Supports both console output and file logging with rotation.
"""

import logging
import sys
from pathlib import Path
from typing import Any

from app.core.config import settings

# 日志文件目录
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)


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
            },
            "detailed": {
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s",
            },
        }
        default_formatter = "simple"

    # 日志文件路径
    log_file = str(LOG_DIR / "app.log")
    collect_log_file = str(LOG_DIR / "collect.log")

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": formatters,
        "handlers": {
            # 控制台输出
            "console": {
                "class": "logging.StreamHandler",
                "stream": sys.stdout,
                "formatter": default_formatter,
            },
            # 主日志文件（轮转，最大 10MB，保留 5 个备份）
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": log_file,
                "maxBytes": 10 * 1024 * 1024,  # 10MB
                "backupCount": 5,
                "formatter": "detailed",
                "encoding": "utf-8",
            },
            # 采集任务专用日志文件
            "collect_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "filename": collect_log_file,
                "maxBytes": 50 * 1024 * 1024,  # 50MB (采集日志量大)
                "backupCount": 3,
                "formatter": "detailed",
                "encoding": "utf-8",
            },
        },
        "loggers": {
            "app": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            # 采集模块单独配置，输出到专用日志文件
            "app.services.collect": {
                "level": "INFO",
                "handlers": ["console", "collect_file"],
                "propagate": False,
            },
            "app.services.data_fetchers": {
                "level": "INFO",
                "handlers": ["console", "collect_file"],
                "propagate": False,
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "level": "WARNING",
                "handlers": ["console", "file"],
                "propagate": False,
            },
        },
        "root": {
            "level": "INFO",
            "handlers": ["console", "file"],
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
