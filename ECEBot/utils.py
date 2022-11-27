import discord

def error_embed(msg: str) -> discord.Embed:
    return discord.Embed(
        title='Error',
        description=msg,
        color=discord.Color.red(),
    )
