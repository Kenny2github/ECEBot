# stdlib
import time
from functools import partial
from logging import getLogger

# 3rd-party
import discord
from discord import app_commands
from discord.ext import commands

# 1st-party
import config
from .utils import error_embed

SIGNALLED_EXCS = (
    app_commands.BotMissingPermissions,
    app_commands.MissingPermissions,
    app_commands.CommandOnCooldown,
)
UNLOGGED_EXCS = (
    app_commands.CheckFailure,
    app_commands.CommandNotFound,
)

logger = getLogger(__name__)

class ECETree(app_commands.CommandTree):
    async def on_error(
        self, ctx: discord.Interaction, exc: Exception
    ) -> None:
        logger.error('Ignoring exception in command %r - %s: %s',
                    ctx.command.qualified_name if ctx.command else 'None',
                    type(exc).__name__, exc)
        if ctx.command and ctx.command.on_error:
            return # on_error called
        if isinstance(exc, SIGNALLED_EXCS):
            if ctx.response.is_done():
                method = ctx.followup.send
            else:
                method = partial(ctx.response.send_message, ephemeral=True)
            await method(embed=error_embed(str(exc)))
            return
        if isinstance(exc, UNLOGGED_EXCS):
            return
        logger.error('', exc_info=exc)

    async def interaction_check(self, ctx: discord.Interaction) -> bool:
        logger.info('User %s\t(%18d) in channel %s\t(%18d) running /%s',
                    ctx.user, ctx.user.id, ctx.channel,
                    ctx.channel.id if ctx.channel else '(none)',
                    ctx.command.qualified_name if ctx.command else '(none)')
        return True

class ECEBot(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            command_prefix='/',
            help_command=None,
            intents=discord.Intents.default(),
            tree_cls=ECETree
        )

    async def setup_hook(self) -> None:
        if config.DEBUG_GUILD:
            debug_guild = discord.Object(config.DEBUG_GUILD)
            self.tree.copy_global_to(guild=debug_guild)
            await self.tree.sync(guild=debug_guild)
            logger.info('Synced commands')
        now = time.time()
        now_str = time.strftime('%Y-%m-%d %H:%M', time.gmtime(now))
        freshness_str = time.strftime(
            '%Y-%m-%d %H:%M', time.gmtime(config.COMMAND_FRESHNESS))
        if config.COMMAND_FRESHNESS > now:
            logger.info(
                'Command freshness (%s) is newer than current time '
                '(%s), syncing global commands',
                freshness_str, now_str
            )
            await self.tree.sync()
        else:
            logger.debug('Commands are up-to-date (%s < %s)',
                         freshness_str, now_str)

    async def on_ready(self) -> None:
        logger.info('Ready!')

bot = ECEBot()
