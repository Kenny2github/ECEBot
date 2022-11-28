# stdlib
import re

# 3rd-party
import discord
from discord.ext import commands
from discord import app_commands

# 1st-party
from ..controller.role_assignment import COURSES

class Setup(app_commands.Group):

    def __init__(self) -> None:
        super().__init__(
            name='setup',
            description='Perform server setup tasks',
            guild_only=True,
        )

    @app_commands.command()
    async def channels(self, ctx: discord.Interaction) -> None:
        """Set up area categories and course channels."""

    @app_commands.command()
    async def roles(self, ctx: discord.Interaction) -> None:
        """Set up area and course roles."""

class Teardown(app_commands.Group):

    def __init__(self) -> None:
        super().__init__(
            name='teardown',
            description='Tear down items, to set them up again',
            guild_only=True,
        )

    @app_commands.command()
    async def category(self, ctx: discord.Interaction,
                       cat: discord.CategoryChannel) -> None:
        """Tear down a category and all its subchannels."""
        await ctx.response.defer()
        for channel in cat.channels:
            await channel.delete()
        await cat.delete()
        await ctx.edit_original_response(
            content=f'Deleted {cat.name!r} and its members.')

    @app_commands.command()
    async def roles(self, ctx: discord.Interaction, pattern: str) -> None:
        """Tear down all roles matching a regex."""
        assert ctx.guild is not None
        await ctx.response.defer()
        deleted: list[str] = []
        for role in ctx.guild.roles:
            if re.search(pattern, role.name):
                await role.delete()
                deleted.append(role.name)
        await ctx.edit_original_response(
            content='Deleted: ```\n' + '\n'.join(deleted) + '\n```')

def setup(bot: commands.Bot) -> None:
    bot.tree.add_command(Setup())
    bot.tree.add_command(Teardown())
