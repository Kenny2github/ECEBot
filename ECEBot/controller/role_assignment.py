# stdlib
import re
from logging import getLogger
import json
import tomllib
from collections import defaultdict
from typing import Optional, Literal, cast

# 3rd-party
import discord
from discord.ext import commands

# 1st-party
from ..utils import error_embed

logger = getLogger(__name__)

Level = Literal[200, 300, 400, 500]

MESSAGE_FILENAME = 'messages.json'
COURSES_FILENAME = 'courses.toml'

GIVEN_MESSAGE = 'Gave %r (%s) role to %s (%s)'
REMOVED_MESSAGE = 'Removed %r (%s) role from %s (%s)'
HAD_MESSAGE = '%r (%s) role already given to %s (%s)'
NOT_HAD_MESSAGE = '%r (%s) role not present on %s (%s)'

# load course info

COURSES: dict[int, defaultdict[Level, list[str]]] = {}
with open(COURSES_FILENAME, 'rb') as f:
    courses = tomllib.load(f)

course = code = ''
area = level = 0
for area in range(1, 8):
    COURSES[area] = defaultdict(list)
    for course in courses[f'area-{area}']['courses']:
        code = re.search(r'[2345]\d\d', course)
        if code is None:
            raise ValueError(f'Invalid course code {course!r}')
        level = cast(Level, int(code.group(0)[0]) * 100)
        COURSES[area][level].append(course)
        logger.info('Area %s: loaded %s-level %s',
                    area, level, course)

del courses, course, area, code, level

# end course info

class AreaView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(options=[
        discord.SelectOption(label={
            1: 'Area 1: Photonics & Semiconductor Physics',
            2: 'Area 2: Electromagnetics & Energy Systems',
            3: 'Area 3: Analog & Digital Electronics',
            4: 'Area 4: Control, Communications & Signal Processing',
            5: 'Area 5: Computer Hardware & Computer Networks',
            6: 'Area 6: Software',
            7: 'Area 7: Science/Math Electives',
        }[i], value=f'{i}')
        for i in range(1, 8)
    ], placeholder='Choose an area')
    async def area(self, ctx: discord.Interaction,
                   select: discord.ui.Select) -> None:
        assert ctx.guild is not None
        assert ctx.message is not None
        assert isinstance(ctx.user, discord.Member)
        view = LevelView(area=int(select.values[0]))
        await ctx.response.edit_message(view=self)
        await ctx.followup.send(
            content=f'Choose Area {select.values[0]} courses from the below dropdowns.',
            view=view,
            ephemeral=True,
        )

class LevelView(discord.ui.View):

    area: int

    def __init__(self, *, area: int, timeout: Optional[float] = 180):
        super().__init__(timeout=timeout)
        self.area = area
        for level in 200, 300, 400, 500:
            courses = COURSES[self.area][level]
            if courses:
                self.add_item(CourseSelect(
                    level=level, courses=courses))

class CourseSelect(discord.ui.Select[LevelView]):

    def __init__(self, *, level: Level, courses: list[str]) -> None:
        super().__init__(
            placeholder=f'{level}-level courses',
            options=[discord.SelectOption(label=course)
                     for course in courses]
        )

    async def callback(self, ctx: discord.Interaction) -> None:
        assert ctx.guild is not None
        assert ctx.message is not None
        assert isinstance(ctx.user, discord.Member)
        name = self.values[0]
        role = discord.utils.get(ctx.guild.roles, name=name)
        await ctx.response.edit_message(view=self.view)
        if role is None:
            await ctx.followup.send(embed=error_embed(
                f'Could not find {name!r} role to toggle, '
                'please contact the admins.'))
            return
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
                await message.edit(view=AreaView())
            except discord.NotFound:
                logger.error('Message ID %s not found, unsetting', message.id)
                del data[str(channel_id)] # clear this message
                continue
    finally:
        with open(MESSAGE_FILENAME, 'w', encoding='utf8') as f:
            json.dump(data, f)
        logger.debug('Written updated data')
