# stdlib
from logging import getLogger

# 3rd-party
import discord
from discord.ext import commands
from discord import app_commands

# 1st-party
from ..controller.role_assignment import REMOVED_MESSAGE, GIVEN_MESSAGE
from ..controller.course_creation import COURSES, course_amc, add_course
from ..utils import error_embed

logger = getLogger(__name__)

def indexes_of(search: str, value: str) -> list[int]:
    """Check whether ``search`` matches ``value``.
    Return the indexes at which it matched, or an empty list if any didn't.

    Examples:
        >>> indexes_of('sdmsg', 'send_message')
        [0, 3, 5, 7, 10]
        >>> indexes_of('sen', 'send_message')
        [0, 1, 2]
        >>> indexes_of('odmsg', 'send_message') # no "o"
        []
        >>> indexes_of('sgm', 'send_message') # out of order
        []
    """
    if search == '':
        return []
    indexes = [value.find(search[0])]
    if indexes[-1] == -1:
        # character not found
        return []
    for c in search[1:]:
        new_index = value.find(c, indexes[-1])
        if new_index == -1:
            # character not found
            return []
        indexes.append(new_index)
    return indexes

async def course_complete(
    ctx: discord.Interaction, value: str
) -> list[app_commands.Choice[str]]:
    """Autocomplete options for course parameter"""
    assert ctx.guild is not None
    assert isinstance(ctx.user, discord.Member)
    value = value.upper() # for convenience

    choices: list[str] = []
    courses = [course for levels in COURSES.values()
               for courses in levels.values() for course in courses]
    for course in courses:
        if course in choices:
            continue
        if value == '' or indexes_of(value, course): # empty list is no match
            choices.append(course)
        if len(choices) == 25:
            # Hit limit of number of choices
            break
    # sort by closeness of match, then lexicographically
    choices.sort(key=lambda choice: (indexes_of(value, choice), choice))
    logger.debug('Suggesting %s choice(s) to %s from input %r',
                    len(choices), ctx.user, value)
    return [app_commands.Choice(name=choice, value=choice)
            for choice in choices]

class SelfRole(commands.Cog):

    @app_commands.guild_only()
    @app_commands.command()
    async def course_role(self, ctx: discord.Interaction, course: str) -> None:
        """Give yourself a course role!"""
        assert ctx.guild is not None
        assert isinstance(ctx.user, discord.Member)

        role = discord.utils.get(ctx.guild.roles, name=course)
        if role is None:
            # maybe create the role and channel for the course
            courses = {course for levels in COURSES.values()
                       for courses in levels.values() for course in courses}
            if course not in courses:
                # don't create roles/channels for nonexistent courses
                await ctx.response.send_message(embed=error_embed(
                    f'No such course: {course!r}'
                ), ephemeral=True)
                return
            await ctx.response.defer(ephemeral=True)
            role, _ = await add_course(ctx.guild, course_amc(course), course)
        else:
            await ctx.response.defer(ephemeral=True)
        # toggle the role
        if role in ctx.user.roles:
            await ctx.user.remove_roles(role, reason='Requested by user')
            logger.info(REMOVED_MESSAGE, course, role.id, ctx.user, ctx.user.id)
            await ctx.edit_original_response(
                content=f'Successfully removed your {course!r} role.')
        else:
            await ctx.user.add_roles(role, reason='Requested by user')
            logger.info(GIVEN_MESSAGE, course, role.id, ctx.user, ctx.user.id)
            await ctx.edit_original_response(
                content=f'Successfully gave you the {course!r} role.')

    @course_role.autocomplete('course')
    async def course_role_autocomplete(
        self, ctx: discord.Interaction, value: str
    ) -> list[app_commands.Choice[str]]:
        return await course_complete(ctx, value)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SelfRole())
