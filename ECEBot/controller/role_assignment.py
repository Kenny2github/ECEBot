# stdlib
from logging import getLogger
import json
from typing import Optional, cast

# 3rd-party
import discord
from discord.ext import commands

# 1st-party
from .course_creation import add_course, load_course_info, \
    AREAS, MINORS_CERTS, COURSES
from ..utils import Category, Level

logger = getLogger(__name__)

MESSAGE_FILENAME = 'messages.json'

GIVEN_MESSAGE = 'Gave %r (%s) role to %s (%s)'
REMOVED_MESSAGE = 'Removed %r (%s) role from %s (%s)'
HAD_MESSAGE = '%r (%s) role already given to %s (%s)'
NOT_HAD_MESSAGE = '%r (%s) role not present on %s (%s)'

load_course_info()

class CategoryView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(options=[
        discord.SelectOption(label=area, value=f'{i}')
        for i, area in AREAS.items()
    ], placeholder='Choose an area')
    async def area(self, ctx: discord.Interaction,
                   select: discord.ui.Select) -> None:
        await self._category(ctx, int(select.values[0]),
                             f'Area {select.values[0]}')

    @discord.ui.select(options=[
        discord.SelectOption(label=name, value=key)
        for key, name in MINORS_CERTS.items()
    ], placeholder='Choose a minor/certificate')
    async def minor_cert(self, ctx: discord.Interaction,
                         select: discord.ui.Select) -> None:
        await self._category(ctx, select.values[0],
                             MINORS_CERTS[select.values[0]])

    async def _category(self, ctx: discord.Interaction,
                        key: Category, value: str) -> None:
        assert ctx.guild is not None
        assert ctx.message is not None
        assert isinstance(ctx.user, discord.Member)
        view = LevelView(category=key)
        await ctx.response.edit_message(view=self)
        await ctx.followup.send(
            content=f'Choose {value} courses from the below dropdowns.',
            view=view,
            ephemeral=True,
        )

class LevelView(discord.ui.View):

    def __init__(self, *, category: Category, timeout: Optional[float] = 180):
        super().__init__(timeout=timeout)
        for level in 100, 200, 300, 400, 500:
            courses = COURSES[category][level]
            if courses:
                self.add_item(CourseSelect(
                    category=category, level=level, courses=courses))

class CourseSelect(discord.ui.Select[LevelView]):

    category: Category

    def __init__(self, *, category: Category,
                 level: Level, courses: list[str]) -> None:
        super().__init__(
            placeholder=f'{level}-level courses',
            options=[discord.SelectOption(label=course)
                     for course in courses]
        )
        self.category = category

    async def callback(self, ctx: discord.Interaction) -> None:
        assert ctx.guild is not None
        assert ctx.message is not None
        assert isinstance(ctx.user, discord.Member)
        name = self.values[0]
        role = discord.utils.get(ctx.guild.roles, name=name)
        await ctx.response.edit_message(view=self.view)
        if role is None:
            # create missing role and channel on demand
            role, _ = await add_course(ctx.guild, self.category, name, True)
        if role in ctx.user.roles:
            await ctx.user.remove_roles(role, reason='Requested by user')
            logger.info(REMOVED_MESSAGE, name, role.id, ctx.user, ctx.user.id)
            await ctx.followup.send(
                content=f'Successfully removed your {name!r} role.', ephemeral=True)
        else:
            await ctx.user.add_roles(role, reason='Requested by user')
            logger.info(GIVEN_MESSAGE, name, role.id, ctx.user, ctx.user.id)
            await ctx.followup.send(
                content=f'Successfully gave you the {name!r} role.', ephemeral=True)

async def load_guilds(bot: commands.Bot) -> None:
    data = {}
    try:
        with open(MESSAGE_FILENAME, 'r', encoding='utf8') as f:
            data: dict[str, int] = json.load(f)
    except FileNotFoundError:
        logger.warning('No guild data to load')
        return
    else:
        # to prevent modifying a dictionary we're iterating over
        data_items = list(data.items())
        for channel_id, message_id in data_items:
            channel_id = int(channel_id)
            try:
                channel = cast(discord.TextChannel, bot.get_channel(channel_id)
                               or await bot.fetch_channel(channel_id))
            except discord.NotFound:
                logger.error('Channel ID %s not found, unsetting', channel_id)
                del data[str(channel_id)] # clear this channel
                continue
            message = channel.get_partial_message(message_id)
            logger.info('Taking ownership of #%s (%s) %s',
                        channel.name, channel.id, message.id)
            try:
                await message.edit(view=CategoryView())
            except discord.NotFound:
                logger.error('Message ID %s not found, unsetting', message.id)
                del data[str(channel_id)] # clear this message
                continue
    finally:
        with open(MESSAGE_FILENAME, 'w', encoding='utf8') as f:
            json.dump(data, f)
        logger.debug('Written updated data')
