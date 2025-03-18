import discord
from discord import Interaction, app_commands

from ..core.exceptions import NotEnoughPermissions, UserNotOwner


def is_owner():
    def predicate(interaction: Interaction) -> bool:
        if interaction.user.id not in interaction.client.config.OWNERS:
            raise UserNotOwner
        return True

    return app_commands.check(predicate)


def is_guild_admin():
    def predicate(interaction: Interaction) -> bool:
        if interaction.user.guild_permissions.administrator:
            return True
        raise NotEnoughPermissions(
            "You need to have administrator permissions to use this command."
        )

    return app_commands.check(predicate)


async def set_role(
    guild: discord.Guild,
    name: str,
    color: discord.Color = discord.Color.default(),
    hoist: bool = False,
    mentionable: bool = False,
    reason: str = None,
) -> discord.Role:
    for role in guild.roles:
        if role.name == name:
            await role.delete()
            break
    return await guild.create_role(
        name=name, color=color, hoist=hoist, mentionable=mentionable, reason=reason
    )


async def reply(interaction: Interaction, content: str, ephemeral: bool = True):
    if interaction.response.is_done():
        await interaction.followup.send(content, ephemeral=ephemeral)
    else:
        await interaction.response.send_message(content, ephemeral=ephemeral)
