from pathlib import Path

from discord import Intents
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class BotSettings(BaseSettings):
    ENV: str = "prod"
    INTENTS: int = Intents.default().value
    TOKEN: SecretStr = SecretStr("")

    BASE_PATH: str = str(Path.cwd())

    DESCRIPTION: str = "A simple bot"
    APPLICATION_ID: int = 0
    PERMISSIONS: int = 0
    SYNC_COMMANDS_GLOBALLY: bool = False
    STATUS: list[str] = [
        "fishing",
        "fishing a fish",
        "fishing a fish fishing",
        "fishing a fish fishing a fish",
        "fishing a SpongeBob!!!",
    ]
    USE_TRANSLATOR: bool = True
    DEV_CHANNEL_ID: int | None = None
    DEV_GUILD_ID: int | None = None
    OWNERS: list[int] = []

    model_config = SettingsConfigDict(
        env_prefix="BOT_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @property
    def DEBUG(self) -> bool:
        return True if self.ENV == "dev" else False


bot_settings = BotSettings()
