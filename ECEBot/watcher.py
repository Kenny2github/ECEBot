# stdlib
import os
from typing import Optional
from logging import getLogger
import asyncio

# 3rd-party
from discord.ext import commands

logger = getLogger(__name__)

def recurse_mtimes(dir: str, *path: str,
                   current: Optional[dict[str, float]] = None
                   ) -> dict[str, float]:
    """Recursively get the mtimes of all files of interest."""
    if current is None:
        current = {}
    for item in os.listdir(os.path.join(*path, dir)):
        fullitem = os.path.join(*path, dir, item)
        if os.path.isdir(fullitem):
            recurse_mtimes(item, *path, dir, current=current)
        elif item.endswith(('.py', '.sql', '.json')):
            current[fullitem] = os.path.getmtime(fullitem)
    return current

async def stop_on_change(bot: commands.Bot, path: str):
    mtimes = recurse_mtimes(path)
    while 1:
        for fn, mtime in mtimes.items():
            try:
                newmtime = os.path.getmtime(fn)
            except FileNotFoundError:
                logger.info("File '%s' deleted, closing client", fn)
                await bot.close()
                return
            if newmtime > mtime:
                logger.info("File '%s' modified, closing client", fn)
                await bot.close()
                return
        await asyncio.sleep(1)
