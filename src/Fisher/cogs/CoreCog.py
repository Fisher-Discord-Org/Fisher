from importlib import import_module
from importlib.metadata import packages_distributions

from discord import Colour, Interaction, Locale, app_commands

from ..core.exceptions import CommandArgumentError, FisherExitCommand
from ..core.Fisher import Fisher, FisherCog, logger
from ..utils.discord_utils import is_owner
from ..utils.view import PaginationEmbed


class CoreCog(
    FisherCog,
    name="core",
    description="Core cog of the bot that contains basic commands. (Note: This cog is not meant and cannot be disabled.)",
):
    def __init__(self, bot: Fisher) -> None:
        super().__init__(bot, requires_db=True)

    @app_commands.command(
        name="ping",
        description="Ping the bot",
        extras={
            "locale": {
                "name": {
                    Locale.american_english: "ping",
                    Locale.british_english: "ping",
                    Locale.chinese: "ping",
                },
                "description": {
                    Locale.american_english: "Ping the bot",
                    Locale.british_english: "Ping the bot",
                    Locale.chinese: "显示机器人的ping值",
                },
            }
        },
    )
    async def ping(self, interaction: Interaction) -> None:
        await interaction.response.send_message(
            f"Pong! Latency: {self.bot.latency * 1000:.2f}ms"
        )

    @app_commands.command(
        name="exit",
        description="Exit the bot",
        extras={
            "locale": {
                "name": {
                    Locale.american_english: "exit",
                    Locale.british_english: "exit",
                    Locale.chinese: "退出",
                },
                "description": {
                    Locale.american_english: "Exit the bot",
                    Locale.british_english: "Exit the bot",
                    Locale.chinese: "退出机器人",
                },
            }
        },
    )
    @app_commands.guilds(Fisher.config.DEV_GUILD_ID)
    @is_owner()
    async def exit(self, interaction: Interaction) -> None:
        await interaction.response.send_message(f"Bye!", ephemeral=True)
        raise FisherExitCommand

    @app_commands.command(
        name="sync",
        description="Syncronize the slash commands",
        extras={
            "locale": {
                "name": {
                    Locale.american_english: "sync",
                    Locale.british_english: "sync",
                    Locale.chinese: "同步",
                },
                "description": {
                    Locale.american_english: "Syncronize the slash commands",
                    Locale.british_english: "Syncronize the slash commands",
                    Locale.chinese: "同步命令",
                },
                "parameters": {
                    "guild_id": {
                        "name": {
                            Locale.american_english: "guild_id",
                            Locale.british_english: "guild_id",
                            Locale.chinese: "服务器",
                        },
                        "description": {
                            Locale.american_english: "id of the guild you want to sync the commands to",
                            Locale.british_english: "id of the guild you want to sync the commands to",
                            Locale.chinese: "要同步命令的服务器ID",
                        },
                    }
                },
            }
        },
    )
    @app_commands.describe(guild_id="id of the guild you want to sync the commands to")
    @app_commands.guilds(Fisher.config.DEV_GUILD_ID)
    @is_owner()
    async def sync_command(
        self, interaction: Interaction, guild_id: str | None = None
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        if guild_id is None:
            await self.bot.tree.sync()
            await interaction.followup.send(
                content="Slash commands have been globally synchronized.",
                ephemeral=True,
            )
            return
        if not guild_id.isdigit():
            raise CommandArgumentError(status_code=400, detail="Invalid guild ID.")
        guild = self.bot.get_guild(int(guild_id))
        if not guild:
            raise CommandArgumentError(status_code=400, detail="Invalid guild ID.")
        await self.bot.tree.sync(guild=guild)
        await interaction.followup.send(
            content=f"Slash commands have been synchronized in {guild}.", ephemeral=True
        )

    @app_commands.command(
        name="list_cog",
        description="List all enabled cogs",
        extras={
            "locale": {
                "name": {
                    Locale.american_english: "list_cog",
                    Locale.british_english: "list_cog",
                    Locale.chinese: "列出组件",
                },
                "description": {
                    Locale.american_english: "List all enabled cogs",
                    Locale.british_english: "List all enabled cogs",
                    Locale.chinese: "列出所有已启用的组件",
                },
                "parameters": {
                    "option": {
                        "name": {
                            Locale.american_english: "option",
                            Locale.british_english: "option",
                            Locale.chinese: "选项",
                        },
                        "description": {
                            Locale.american_english: "option to list enabled or disabled cogs",
                            Locale.british_english: "option to list enabled or disabled cogs",
                            Locale.chinese: "列出已启用或未启用的组件",
                        },
                        "choices": {
                            "enabled": {
                                "name": {
                                    Locale.american_english: "enabled",
                                    Locale.british_english: "enabled",
                                    Locale.chinese: "仅启用",
                                },
                            },
                            "disabled": {
                                "name": {
                                    Locale.american_english: "disabled",
                                    Locale.british_english: "disabled",
                                    Locale.chinese: "仅未启用",
                                },
                            },
                        },
                    }
                },
            }
        },
    )
    @app_commands.describe(option="option to list enabled or disabled cogs")
    @app_commands.choices(
        option=[
            app_commands.Choice(name="enabled", value="enabled"),
            app_commands.Choice(name="disabled", value="disabled"),
        ]
    )
    @is_owner()
    async def list_cog(self, interaction: Interaction, option: str = "enabled"):
        await interaction.response.defer(ephemeral=True)
        embed = PaginationEmbed(title=f"Cog List ({option})", color=Colour.dark_blue())
        if option == "enabled":
            for cog_name, cog in self.bot.cogs.items():
                embed.add_field(name=cog_name, value=cog.description, inline=False)
            await interaction.followup.send(
                embed=embed.initial_embed, view=embed, ephemeral=True
            )
            return

        distributions_packages = self.__distributions_packages()
        for dist in distributions_packages:
            for package in distributions_packages[dist]:
                try:
                    module = import_module(".cogs", package=package)
                    cogs = [cog for cog in dir(module) if not cog.startswith("__")]
                    for cog in cogs:
                        cog_class = getattr(module, cog)
                        if (
                            issubclass(cog_class, FisherCog)
                            and cog_class.__cog_name__ not in self.bot.cogs
                        ):
                            embed.add_field(
                                name=cog_class.__cog_name__,
                                value=f"""
                                dist: `{dist}`
                                package: `{package}.cogs.{cog_class.__name__}`
                                description: {cog_class.__cog_description__}
                                """,
                                inline=False,
                            )
                except ImportError:
                    logger.warning(f"Skipping {package} due to ImportError.")
        await interaction.followup.send(
            embed=embed.initial_embed, view=embed, ephemeral=True
        )

    @app_commands.command(
        name="enable",
        description="Enable a cog",
        extras={
            "locale": {
                "name": {
                    Locale.american_english: "enable",
                    Locale.british_english: "enable",
                    Locale.chinese: "启用",
                },
                "description": {
                    Locale.american_english: "Enable a cog",
                    Locale.british_english: "Enable a cog",
                    Locale.chinese: "启用组件",
                },
                "parameters": {
                    "cog_name": {
                        "name": {
                            Locale.american_english: "cog_name",
                            Locale.british_english: "cog_name",
                            Locale.chinese: "组件名称",
                        },
                        "description": {
                            Locale.american_english: "additional cog you want to enable",
                            Locale.british_english: "additional cog you want to enable",
                            Locale.chinese: "要启用的组件",
                        },
                    }
                },
            }
        },
    )
    @app_commands.describe(cog_name="additional cog you want to enable")
    @is_owner()
    async def enable_cog(self, interaction: Interaction, cog_name: str):
        await interaction.response.defer(ephemeral=True)
        if cog_name in self.bot.cogs:
            raise CommandArgumentError(
                status_code=400, detail=f"Cog `{cog_name}` is already enabled."
            )
        if not await self.__load_cog(cog_name):
            raise CommandArgumentError(
                status_code=400, detail=f"Cog `{cog_name}` does not exist."
            )

        await interaction.followup.send(
            f"Cog `{cog_name}` has been enabled.", ephemeral=True
        )

    @app_commands.command(
        name="disable",
        description="Disable a cog",
        extras={
            "locale": {
                "name": {
                    Locale.american_english: "disable",
                    Locale.british_english: "disable",
                    Locale.chinese: "禁用",
                },
                "description": {
                    Locale.american_english: "Disable a cog",
                    Locale.british_english: "Disable a cog",
                    Locale.chinese: "禁用组件",
                },
                "parameters": {
                    "cog_name": {
                        "name": {
                            Locale.american_english: "cog_name",
                            Locale.british_english: "cog_name",
                            Locale.chinese: "组件名称",
                        },
                        "description": {
                            Locale.american_english: "cog you want to disable",
                            Locale.british_english: "cog you want to disable",
                            Locale.chinese: "要禁用的组件",
                        },
                    }
                },
            }
        },
    )
    @app_commands.describe(cog_name="cog you want to disable")
    @is_owner()
    async def disable_cog(self, interaction: Interaction, cog_name: str):
        await interaction.response.defer(ephemeral=True)
        if cog_name not in self.bot.cogs:
            raise CommandArgumentError(
                status_code=400,
                detail=f"Cog `{cog_name}` does not exist or is not enabled.",
            )
        elif cog_name == "core":
            raise CommandArgumentError(
                status_code=400, detail="Cog `core` cannot be disabled."
            )
        await self.bot.remove_cog(cog_name)
        await interaction.followup.send(
            f"Cog `{cog_name}` has been disabled.", ephemeral=True
        )

    @app_commands.command(
        name="reload",
        description="Reload a cog",
        extras={
            "locale": {
                "name": {
                    Locale.american_english: "reload",
                    Locale.british_english: "reload",
                    Locale.chinese: "重载",
                },
                "description": {
                    Locale.american_english: "Reload a cog",
                    Locale.british_english: "Reload a cog",
                    Locale.chinese: "重载组件",
                },
                "parameters": {
                    "cog_name": {
                        "name": {
                            Locale.american_english: "cog_name",
                            Locale.british_english: "cog_name",
                            Locale.chinese: "组件名称",
                        },
                        "description": {
                            Locale.american_english: "cog you want to reload",
                            Locale.british_english: "cog you want to reload",
                            Locale.chinese: "要重载的组件",
                        },
                    }
                },
            }
        },
    )
    @app_commands.describe(cog_name="cog you want to reload")
    @is_owner()
    async def reload_cog(self, interaction: Interaction, cog_name: str):
        await interaction.response.defer(ephemeral=True)
        if cog_name not in self.bot.cogs:
            raise CommandArgumentError(
                status_code=400,
                detail=f"Cog `{cog_name}` does not exist or is not enabled.",
            )
        elif cog_name == "core":
            raise CommandArgumentError(
                status_code=400,
                detail="Cog `core` cannot be reloaded. Please restart the bot to reload the core cog.",
            )

        await self.bot.remove_cog(cog_name)

        if not await self.__load_cog(cog_name):
            raise CommandArgumentError(
                status_code=400, detail=f"Cog `{cog_name}` does not exist."
            )

        await interaction.followup.send(
            f"Cog `{cog_name}` has been reloaded.", ephemeral=True
        )

    def __distributions_packages(self, prefix: str = "fisher-"):
        distributions_packages = {}
        for package, distributions in packages_distributions().items():
            for distribution in distributions:
                if not distribution.lower().startswith(prefix):
                    continue
                if distribution not in distributions_packages:
                    distributions_packages[distribution] = []
                distributions_packages[distribution].append(package)
        return distributions_packages

    async def __load_cog(self, cog_name: str) -> bool:
        distributions_packages = self.__distributions_packages()
        for distribution in distributions_packages:
            for package in distributions_packages[distribution]:
                try:
                    module = import_module(".cogs", package=package)
                except ImportError:
                    logger.warning(f"Skipping {package} due to ImportError.")
                    continue
                cogs = [cog for cog in dir(module) if not cog.startswith("__")]
                for cog in cogs:
                    cog_class = getattr(module, cog)
                    if (
                        issubclass(cog_class, FisherCog)
                        and cog_class.__cog_name__ == cog_name
                    ):
                        try:
                            await self.bot.add_cog(cog_class(self.bot))
                            return True
                        except Exception as e:
                            logger.error(f"Failed to load cog [{cog_name}]")
                            logger.exception(f"{type(e).__name__}: {e}")
                            raise CommandArgumentError(
                                status_code=500,
                                detail=f"Cog `{cog_name}` found but failed to load due to an internal error.",
                            )
        return False
