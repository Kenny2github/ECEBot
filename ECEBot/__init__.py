# stdlib
import importlib
import asyncio
from logging import getLogger
from typing import TypedDict

# 3rd-party
from discord.ext import commands

# 1st-party
from .client import bot
from config import TOKEN
from .logs import activate as activate_logging
from .status import SetStatus
from .watcher import stop_on_change
from .controller.role_assignment import load_guilds

MODULES: dict[str, tuple[str, str]] = {
    'Miscellaneous Commands': ('cmd.misc', 'misc'),
    'Message Sending': ('cmd.message_sending', 'msg'),
}

logger = getLogger(__name__)

async def import_cog(bot: commands.Bot, name: str, fname: str):
    """Load a module and run its setup function."""
    module = importlib.import_module('.' + fname, __name__)
    if asyncio.iscoroutinefunction(module.setup):
        await module.setup(bot)
    else:
        module.setup(bot)
    logger.info('Loaded %s', name)

class Globs(TypedDict, total=False):
    logger: asyncio.Task[None]
    status: SetStatus
    wakeup: asyncio.Task[None]

globs: Globs = {}

async def run():
    """Run the bot."""
    globs['logger'] = activate_logging() # NOTE: Do this first
    for name, (fname, cmdname) in MODULES.items():
        await import_cog(bot, name, fname)
    globs['status'] = SetStatus(bot)
    globs['wakeup'] = asyncio.create_task(stop_on_change(bot, 'ECEBot'))
    await bot.login(TOKEN)
    globs['status'].start()
    asyncio.create_task(load_guilds(bot))
    await bot.connect()

async def cleanup_tasks():
    for task in asyncio.all_tasks():
        try:
            # note that this cancels the task on timeout
            await asyncio.wait_for(task, 3.0)
        except asyncio.TimeoutError:
            pass
        except asyncio.CancelledError:
            return

async def done():
    """Cleanup and shutdown the bot."""
    try:
        if 'wakeup' in globs:
            globs['wakeup'].cancel()
        if 'status' in globs:
            globs['status'].cancel()
        if 'logger' in globs:
            globs['logger'].cancel()
    except RuntimeError as exc:
        print(exc)
    await bot.close()
    await cleanup_tasks()
