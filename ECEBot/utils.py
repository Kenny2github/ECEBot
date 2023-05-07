# stdlib
from typing import Union

# 3rd-party
import discord

def error_embed(msg: str) -> discord.Embed:
    return discord.Embed(
        title='Error',
        description=msg,
        color=discord.Color.red(),
    )

Category = Union[int, str]
