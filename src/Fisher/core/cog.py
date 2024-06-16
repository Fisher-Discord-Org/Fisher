from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from discord import app_commands
from discord.ext.commands import Cog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from .singleton import Singleton, SingletonCogMeta
from .translator import Corpus

if TYPE_CHECKING:
    from .Fisher import Fisher


class FisherCog(Cog, Singleton, metaclass=SingletonCogMeta):
    def __init__(self, bot: Fisher, requires_db: bool = False):
        self.bot = bot
        self.__corpus = Corpus()
        self.requires_db = requires_db

    async def cog_load(self) -> None:
        commands_queue = self.get_app_commands()
        for node in commands_queue:
            if isinstance(node, app_commands.Group):
                commands_queue.extend(node.commands)
                await self._register_group_corpus(node)
            elif isinstance(node, app_commands.Command):
                await self._register_command_corpus(node)
            else:
                raise TypeError(f"Invalid type {type(node)}")
        self.bot.tree.translator.update_corpus(self.__corpus)
        if self.requires_db:
            self.bot.create_db(self)

    async def cog_unload(self) -> None:
        if self.requires_db:
            await self.bot.remove_db(self)

    def __check_db(self):
        if not self.requires_db:
            raise RuntimeError(
                f"Cog [{type(self).__name__}] does not require a database but tried to access it. Please set requires_db to True to use database-related methods."
            )

    @asynccontextmanager
    async def db_session(self) -> AsyncIterator[AsyncSession]:
        self.__check_db()

        db_engine = self.bot.get_db(self)
        async with db_engine.Session() as session:
            yield session

    async def init_models(self, base_cls: type[DeclarativeBase]) -> None:
        self.__check_db()

        db_engine = self.bot.get_db(self)
        await db_engine.init_models(base_cls)

    async def _register_group_corpus(self, group: app_commands.Group) -> None:
        if "locale" not in group.extras:
            return
        if "name" in group.extras["locale"]:
            self.__corpus.add_group_name(group.name, group.extras["locale"]["name"])
        if "description" in group.extras["locale"]:
            self.__corpus.add_group_description(
                group.description, group.extras["locale"]["description"]
            )

    async def _register_command_corpus(self, command: app_commands.Command) -> None:
        if "locale" not in command.extras:
            return
        if "name" in command.extras["locale"]:
            self.__corpus.add_command_name(
                command.name, command.extras["locale"]["name"]
            )
        if "description" in command.extras["locale"]:
            self.__corpus.add_command_description(
                command.description, command.extras["locale"]["description"]
            )
        await self._register_parameters_corpus(
            command.parameters, command.extras["locale"].get("parameters", {})
        )

    async def _register_parameters_corpus(
        self, parameters: list[app_commands.Parameter], locale_dict: dict[str, dict]
    ) -> None:
        for parameter in parameters:
            if parameter.name not in locale_dict:
                continue
            if "name" in locale_dict[parameter.name]:
                self.__corpus.add_parameter_name(
                    parameter.name, locale_dict[parameter.name]["name"]
                )
            if "description" in locale_dict[parameter.name]:
                self.__corpus.add_parameter_description(
                    parameter.description,
                    locale_dict[parameter.name]["description"],
                )
            await self._register_choices_corpus(
                parameter.choices, locale_dict[parameter.name].get("choices", {})
            )

    async def _register_choices_corpus(
        self, choices: list[app_commands.Choice], locale_dict: dict[str, dict]
    ):
        for choice in choices:
            if choice.name not in locale_dict:
                continue
            if "name" in locale_dict[choice.name]:
                self.__corpus.add_choice_name(
                    choice.name, locale_dict[choice.name]["name"]
                )
