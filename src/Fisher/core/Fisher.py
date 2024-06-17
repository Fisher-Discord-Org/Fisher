from __future__ import annotations

import asyncio
import logging
import logging.config
from collections.abc import Coroutine
from functools import partial as func_partial
from os import name as OS_NAME
from platform import python_version, release, system
from random import choice
from signal import SIGINT, SIGTERM, Signals, signal
from time import perf_counter
from types import MappingProxyType
from typing import Mapping, Optional, Sequence

import discord
from discord import app_commands
from discord.abc import Snowflake
from discord.ext import tasks
from discord.ext.commands import Cog, MinimalHelpCommand
from discord.utils import MISSING

from ..config.bot import BotSettings, bot_settings
from ..config.db import DBSettings, SQLiteSettings
from ..config.log import LogSettings
from ..db.database import BaseEngine, SQLiteEngine
from ..utils.discord_utils import reply
from .cog import FisherCog
from .exceptions import CommandArgumentError, FisherExitCommand
from .singleton import Singleton
from .translator import FisherTranslator

logger = logging.getLogger("Fisher")
access_logger = logging.getLogger("Fisher.access")


class Fisher(discord.Client, Singleton):
    config: BotSettings = bot_settings
    log_config: LogSettings = LogSettings()
    db_config: DBSettings = SQLiteSettings()
    __tree: app_commands.CommandTree
    __cogs: dict[str, FisherCog] = {}
    __db: dict[str, BaseEngine] = {}

    def __init__(
        self,
        *,
        loop: asyncio.AbstractEventLoop = None,
        config: BotSettings = BotSettings(),
        **kwargs,
    ):
        super().__init__(
            intents=discord.Intents(config.INTENTS),
            **kwargs,
        )
        self.event_loop = loop or asyncio.get_event_loop()
        self.config = config
        self.termination_event = asyncio.Event()
        self.help_command = MinimalHelpCommand()

        self._setup_coros: list[Coroutine] = []

        self.__tree = app_commands.CommandTree(self)

        logging.config.dictConfig(self.log_config.LOG_CONFIG)

    @property
    def tree(self) -> app_commands.CommandTree:
        return self.__tree

    @property
    def cogs(self) -> Mapping[str, FisherCog]:
        return MappingProxyType(self.__cogs)

    @property
    def dev_guild(self) -> discord.Guild | None:
        return self.get_guild(self.config.DEV_GUILD_ID)

    @property
    def dev_channel(self) -> discord.TextChannel | None:
        return self.get_channel(self.config.DEV_CHANNEL_ID)

    @classmethod
    def get_cogs(cls) -> Mapping[str, FisherCog]:
        return MappingProxyType(cls.__cogs)

    def get_db(self, cog: FisherCog) -> BaseEngine:
        if cog.qualified_name not in self.__db:
            raise KeyError(f"Database for cog {cog.qualified_name} not found.")
        return self.__db[cog.qualified_name]

    def create_db(self, cog: FisherCog) -> None:
        if cog.qualified_name in self.__db:
            raise KeyError(f"Database for cog {cog.qualified_name} already exists.")
        self.__db[cog.qualified_name] = SQLiteEngine(
            cog.qualified_name,
            self.db_config.get_async_url(cog.qualified_name).get_secret_value(),
        )

    async def remove_db(self, cog: FisherCog) -> None:
        if cog.qualified_name not in self.__db:
            raise KeyError(f"Database for cog {cog.qualified_name} not found.")
        await self.__db[cog.qualified_name].db_engine.dispose()
        del self.__db[cog.qualified_name]

    def run(self):
        try:
            self.event_loop.run_until_complete(self.start())
        except asyncio.CancelledError as e:
            logger.info("All tasks are cancelled.")
        except Exception as e:
            logger.exception(f"{type(e).__name__}: {e}")
        finally:
            if not self.termination_event.is_set():
                self.event_loop.run_until_complete(self.stop())

        try:
            tasks = asyncio.all_tasks(self.event_loop)
            for task in tasks:
                task.cancel()
                try:
                    self.event_loop.run_until_complete(task)
                except asyncio.CancelledError:
                    logger.info(f"Task [{task.get_name()}] is cancelled.")
        except Exception as e:
            logger.exception(f"{type(e).__name__}: {e}")
        finally:
            self.event_loop.close()
            logger.info("Event loop closed.")

    async def wait_for_termination(self):
        await self.termination_event.wait()

    def _register_signal_handlers(self):
        def signal_handler(sig, frame):
            logger.info(f"Signal {Signals(sig).name} received.")
            self.event_loop.create_task(self.stop())

        def loop_signal_handler(sig):
            logger.info(f"Signal {Signals(sig).name} received.")
            self.event_loop.create_task(self.stop())

        logger.info("Registering signal handlers for SIGINT and SIGTERM...")
        try:
            self.event_loop.add_signal_handler(
                SIGINT, func_partial(loop_signal_handler, SIGINT)
            )
            self.event_loop.add_signal_handler(
                SIGTERM, func_partial(loop_signal_handler, SIGTERM)
            )
        except NotImplementedError:
            logger.warning(
                f"loop.add_signal_handler() is not implemented on {system()} {release()} ({OS_NAME}). Using signal module instead."
            )
            signal(SIGINT, signal_handler)
            signal(SIGTERM, signal_handler)

    async def start(self):
        self.start_time = perf_counter()
        self.termination_event.clear()
        self._register_signal_handlers()

        logger.info("Starting bot...")
        try:
            await super().start(self.config.TOKEN.get_secret_value())
        except Exception as e:
            e.add_note(f"The above exception occurred during bot startup.")
            raise
        await self.wait_for_termination()

    async def stop(self):
        logger.info(" Stop Phase ".center(60, "-"))

        logger.info("Stopping bot status loop...")
        self.status_task.cancel()
        self.status_task.stop()

        logger.info("Cleaning up cogs...")
        for cog in list(self.__cogs.keys()):
            try:
                await self.remove_cog(cog)
            except Exception as e:
                logger.error(f"Error occurred while removing cog {cog}.")
                logger.exception(e)

        logger.info("Cleaning up db engines...")
        for engine in self.__db.values():
            await engine.db_engine.dispose()
        self.__db.clear()

        logger.info("Closing connection to Discord API...")
        await self.close()

        self.termination_event.set()
        logger.info("Bot stopped.")

    async def setup_hook(self):
        logger.info(" Setup Phase ".center(60, "-"))
        cost_time = perf_counter() * 1000 - self.start_time * 1000
        logger.info(f"Logged in to Discord in {cost_time:.2f}ms")
        logger.info(" Bot Configuration ".center(60, "-"))
        logger.info(f"Name: [{self.user.name}]")
        logger.info(f"discord.py API version: {discord.__version__}")
        logger.info(f"Python version: {python_version()}")
        logger.info(f"Running on: {system()} {release()} ({OS_NAME})")
        logger.info("".center(60, "-"))

        if self.config.USE_TRANSLATOR:
            logger.info("Setting up command tree translator...")
            await self.tree.set_translator(FisherTranslator())

        logger.info("Loading [core] cog...")
        from ..cogs import CoreCog

        await self.add_cog(CoreCog(self))

        async def sync_dev_guild():
            if self.dev_guild is None:
                logger.warning("Invalid dev guild ID. Skipping sync.")
            else:
                logger.info("Syncing dev guild commands...")
                await self.tree.sync(guild=self.dev_guild)

        self._setup_coros.append(sync_dev_guild)

        logger.info("Starting bot status loop...")
        self.status_task.start()

        @self.event
        async def on_app_command_completion(
            interaction: discord.Interaction, command: app_commands.Command
        ):
            access_logger.info(
                f"{interaction.user} ({interaction.user.id}) - {f'{interaction.guild.name} ({interaction.guild.id})' if interaction.guild else 'DMs'} - \"{interaction.command.name}\" 200 \"OK\""
            )

        @self.tree.error
        async def on_app_command_error(
            interaction: discord.Interaction, exception: Exception
        ):
            if isinstance(exception, FisherExitCommand):
                access_logger.info(
                    f"{interaction.user} ({interaction.user.id}) - {f'{interaction.guild.name} ({interaction.guild.id})' if interaction.guild else 'DMs'} - \"{interaction.command.name}\" 200 \"OK\""
                )
                logger.info("Exit command received.")
                await self.stop()
            elif isinstance(exception, app_commands.errors.CheckFailure):
                message = getattr(
                    exception,
                    "message",
                    "You do not have permission to use this command.",
                )
                await reply(interaction, message, ephemeral=True)
                access_logger.info(
                    f"{interaction.user} ({interaction.user.id}) - {f'{interaction.guild.name} ({interaction.guild.id})' if interaction.guild else 'DMs'} - \"{interaction.command.name}\" 403 \"CheckFailure\""
                )
            elif isinstance(exception, CommandArgumentError):
                await reply(interaction, exception.detail, ephemeral=True)
                access_logger.info(
                    f"{interaction.user} ({interaction.user.id}) - {f'{interaction.guild.name} ({interaction.guild.id})' if interaction.guild else 'DMs'} - \"{interaction.command.name}\" {exception.status_code} \"{exception.detail}\""
                )
            elif isinstance(exception, app_commands.errors.CommandNotFound):
                await reply(
                    interaction,
                    f"Command `{exception.name}` not found.\nIt is likely that the command is not available or the cog related to this command is not enabled.",
                    ephemeral=True,
                )
                access_logger.info(
                    f"{interaction.user} ({interaction.user.id}) - {f'{interaction.guild.name} ({interaction.guild.id})' if interaction.guild else 'DMs'} - \"{exception.name}\" 404 \"{type(exception).__name__}\""
                )
            else:
                await reply(interaction, "An internal error occurred.", ephemeral=True)

                access_logger.error(
                    f"{interaction.user} ({interaction.user.id}) - {f'{interaction.guild.name} ({interaction.guild.id})' if interaction.guild else 'DMs'} - \"{interaction.command.name}\" 500 \"{type(exception).__name__}\""
                )
                logger.exception(exception)

    async def on_connect(self):
        logger.info("Connection to Discord API established.")

    async def on_ready(self):
        logger.info(" On_Ready Phase ".center(60, "-"))
        logger.info("Bot internal cache is ready.")
        if self.dev_channel:
            logger.info("Sending connection message to dev channel...")
            await self.dev_channel.send(f"{self.user.name} has connected to Discord!")
        else:
            logger.warning(
                "Invalid dev channel ID. Skipping sending connection message to dev channel."
            )

        logger.info("Waiting for setup tasks to complete...")

        async with asyncio.TaskGroup() as tg:
            for coro in self._setup_coros:
                tg.create_task(coro(), name=coro.__qualname__)

        self._setup_coros.clear()
        logger.info("Setup tasks all done.")

        logger.info("Bot is ready.")

    async def on_error(self, event, *args, **kwargs):
        logger.exception(f"Error occurred in event {event}.")
        if self.dev_channel:
            await self.dev_channel.send(f"Error occurred in event {event}.")

    @tasks.loop(minutes=30.0)
    async def status_task(self):
        try:
            async with asyncio.timeout(10):
                await self.wait_until_ready()
                await self.change_presence(
                    activity=discord.Game(choice(self.config.STATUS))
                )
        except TimeoutError:
            logger.warning("Task 'status_task' timed out.")

    async def add_cog(
        self,
        cog: Cog,
        /,
        *,
        override: bool = False,
        guild: Optional[Snowflake] = MISSING,
        guilds: Sequence[Snowflake] = MISSING,
    ) -> None:
        """Note: This is adopted from discord.ext.commands.Bot.add_cog() method."""
        if not isinstance(cog, Cog):
            raise TypeError("cogs must derive from Cog")

        cog_name = cog.__cog_name__

        if cog_name in self.__cogs:
            if not override:
                raise discord.ClientException(f"Cog named {cog_name!r} already loaded")
            await self.remove_cog(cog_name, guild=guild, guilds=guilds)

        if cog.__cog_app_commands_group__:
            self.tree.add_command(
                cog.__cog_app_commands_group__,
                override=override,
                guild=guild,
                guilds=guilds,
            )
        cog = await cog._inject(self, override=override, guild=guild, guilds=guilds)
        self.__cogs[cog_name] = cog

    def get_cog(self, name: str, /) -> Optional[Cog]:
        """Note: This is adopted from discord.ext.commands.Bot.get_cog() method."""
        return self.__cogs.get(name)

    async def remove_cog(
        self,
        name: str,
        /,
        *,
        guild: Optional[Snowflake] = MISSING,
        guilds: Sequence[Snowflake] = MISSING,
    ) -> Optional[Cog]:
        """Note: This is adopted from discord.ext.commands.Bot.remove_cog() method."""
        if name not in self.__cogs:
            return None
        cog = self.__cogs.pop(name)

        guild_ids = app_commands.tree._retrieve_guild_ids(cog, guild, guilds)

        if cog.__cog_app_commands_group__:
            if not guild_ids:
                self.tree.remove_command(name)
            else:
                for guild_id in guild_ids:
                    self.tree.remove_command(name, guild=discord.Object(id=guild_id))
        await cog._eject(self, guild_ids=guild_ids)

        return cog
