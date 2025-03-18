from os import makedirs
from os.path import join as path_join

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from .bot import bot_settings


class DBSettings(BaseSettings):
    def get_sync_url(self, cog_name: str) -> SecretStr:
        raise NotImplementedError

    def get_async_url(self, cog_name: str) -> SecretStr:
        raise NotImplementedError


class SQLiteSettings(DBSettings):
    SYNC_DRIVER: str = "sqlite"
    ASYNC_DRIVER: str = "sqlite+aiosqlite"
    DIRECTORY: str = "data"

    model_config = SettingsConfigDict(
        env_prefix="SQLITE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_sync_url(self, cog_name: str) -> SecretStr:
        makedirs(path_join(bot_settings.BASE_PATH, self.DIRECTORY), exist_ok=True)
        return SecretStr(
            f"{self.SYNC_DRIVER}:///{path_join(bot_settings.BASE_PATH, self.DIRECTORY, f"{cog_name}.db")}"
        )

    def get_async_url(self, cog_name: str) -> SecretStr:
        makedirs(path_join(bot_settings.BASE_PATH, self.DIRECTORY), exist_ok=True)
        return SecretStr(
            f"{self.ASYNC_DRIVER}:///{path_join(bot_settings.BASE_PATH, self.DIRECTORY, f"{cog_name}.db")}"
        )
