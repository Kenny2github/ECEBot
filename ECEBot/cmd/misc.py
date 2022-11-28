# 3rd-party
import discord
from discord.ext import commands
from discord import app_commands

# 1st-party
from config import INVITE_URL

class Miscellaneous(commands.Cog):

    @app_commands.command()
    async def hello(self, ctx: discord.Interaction) -> None:
        """Test whether the bot is running! Simply says "Hello World!"."""
        await ctx.response.send_message('Hello World!', ephemeral=True)

    if INVITE_URL is not None:
        @app_commands.command()
        @app_commands.default_permissions()
        async def invite(self, ctx: discord.Interaction) -> None:
            """Get an invite link for the bot."""
            await ctx.response.send_message(INVITE_URL, ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Miscellaneous())
