from os import makedirs
from os.path import join as path_join

from pydantic_settings import BaseSettings, SettingsConfigDict

from ..utils.log import ColorFormatter
from .bot import bot_settings


class LogSettings(BaseSettings):
    DIRECTORY: str = "logs"

    model_config = SettingsConfigDict(
        env_prefix="LOG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def LOG_LEVEL(self) -> str:
        return "DEBUG" if bot_settings.DEBUG else "INFO"

    @property
    def LOG_PATH(self) -> str:
        path = path_join(bot_settings.BASE_PATH, self.DIRECTORY)
        makedirs(path, exist_ok=True)
        return path

    @property
    def LOG_FORMATTERS(self) -> dict:
        return {
            "generic": {
                "style": "{",
                "format": "[{asctime}] [{process:^5d}] [{name:^18s}] [{levelname:^8s}] {message:s}",
                "datefmt": "%Y-%m-%d %H:%M:%S %Z",
                "class": "logging.Formatter",
            },
            "color_console": {
                "style": "{",
                "format": "[{asctime}] [{process:^5d}] [{name:^22s}] [{levelname:^20s}] {message:s}",
                "datefmt": "%Y-%m-%d %H:%M:%S %Z",
                "()": ColorFormatter,
            },
        }

    @property
    def LOG_HANDLERS(self) -> dict:
        return {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "generic",
                "stream": "ext://sys.stdout",
            },
            "color_console": {
                "class": "logging.StreamHandler",
                "formatter": "color_console",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "formatter": "generic",
                "filename": path_join(self.LOG_PATH, "access.log"),
                "encoding": "utf-8",
                "when": "midnight",
                "backupCount": 7,
            },
            "error_file": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "formatter": "generic",
                "filename": path_join(self.LOG_PATH, "error.log"),
                "encoding": "utf-8",
                "when": "midnight",
                "backupCount": 7,
            },
        }

    @property
    def LOG_CONFIG(self) -> dict:
        return {
            "version": 1,
            "disable_existing_loggers": False,
            "root": {"level": "INFO", "handlers": ["color_console"]},
            "loggers": {
                "Fisher": {
                    "level": self.LOG_LEVEL,
                    "handlers": ["error_file"],
                    "propagate": True,
                    "qualname": "Fisher",
                },
                "Fisher.access": {
                    "level": "INFO",
                    "handlers": ["file"],
                    "propagate": False,
                    "qualname": "Fisher.access",
                },
                "discord": {
                    "propagate": False,
                },
                "apscheduler": {
                    "level": self.LOG_LEVEL,
                    "handlers": ["error_file"],
                    "propagate": True,
                    "qualname": "apscheduler",
                },
            },
            "handlers": self.LOG_HANDLERS,
            "formatters": self.LOG_FORMATTERS,
        }
