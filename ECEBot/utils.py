# stdlib
from typing import Union, Literal

# 3rd-party
import discord

def error_embed(msg: str) -> discord.Embed:
    return discord.Embed(
        title='Error',
        description=msg,
        color=discord.Color.red(),
    )

Category = Union[int, str]

Level = Literal[100, 200, 300, 400, 500]
