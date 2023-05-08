# stdlib
import json

# 3rd-party
import discord
from discord.ext import commands
from discord import app_commands

# 1st-party
from ..controller.role_assignment import CategoryView, MESSAGE_FILENAME

class MessageModal(discord.ui.Modal):

    body: discord.ui.TextInput
    channel: discord.TextChannel

    def __init__(self, channel: discord.TextChannel) -> None:
        super().__init__(title='Message Body')
        self.channel = channel
        self.body = discord.ui.TextInput(
            label='Text to send',
            style=discord.TextStyle.paragraph,
            placeholder='Choose your roles!',
        )
        self.add_item(self.body)

    async def on_submit(self, ctx: discord.Interaction, /) -> None:
        message = await self.channel.send(self.body.value, view=CategoryView())
        try:
            with open(MESSAGE_FILENAME, 'r', encoding='utf8') as f:
                data: dict[str, int] = json.load(f)
        except FileNotFoundError:
            data = {}
        data[str(self.channel.id)] = message.id
        with open(MESSAGE_FILENAME, 'w', encoding='utf8') as f:
            json.dump(data, f)
        await ctx.response.send_message('Done.', ephemeral=True)

class MessageSending(commands.Cog):

    @app_commands.command()
    @app_commands.guild_only()
    @app_commands.default_permissions()
    @app_commands.describe(channel='The channel to send the message to.')
    async def send_message(self, ctx: discord.Interaction,
                           channel: discord.TextChannel) -> None:
        """Send a message with the area selector in a channel."""
        await ctx.response.send_modal(MessageModal(channel))

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MessageSending())
