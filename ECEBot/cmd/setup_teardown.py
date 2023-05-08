# stdlib
import re
from logging import getLogger

# 3rd-party
import discord
from discord.ext import commands
from discord import app_commands

# 1st-party
from ..controller.role_assignment import COURSES
from ..controller.course_creation import add_course, course_amc
from ..cmd.self_role import course_complete
from ..logs import capture_logs
from ..utils import error_embed

logger = getLogger(__name__)

def tail(logs: list[str], format: str) -> str:
    """Cut down logs to the most recent ones that fit in one message."""
    filtered_logs = [line for line in logs
                     if 'found' not in line.casefold()
                     and 'already' not in line.casefold()]
    if filtered_logs:
        logs = filtered_logs
    msg = format.format('')
    for i in range(1, len(logs) + 1):
        new_msg = format.format('\n'.join(logs[-i:]))
        if len(new_msg) > 2000:
            return msg
        msg = new_msg
    return msg

class Setup(app_commands.Group):

    def __init__(self) -> None:
        super().__init__(
            name='setup',
            description='Perform server setup tasks',
            guild_only=True,
            default_permissions=discord.Permissions.none(),
        )

    @app_commands.command()
    async def channels(self, ctx: discord.Interaction) -> None:
        """Set up area categories and course channels."""
        assert ctx.guild is not None
        missing: set[str] = set()

        area_roles: dict[int, discord.Role] = {}
        for area in range(1, 9):
            name = f'Area {area}'
            role = discord.utils.get(ctx.guild.roles, name=name)
            if role is None:
                missing.add(name)
            else:
                area_roles[area] = role

        course_roles: dict[str, discord.Role] = {}
        courses = {course for area in COURSES.values()
                   for level in area.values() for course in level}
        for course in courses:
            if course in course_roles:
                continue
            role = discord.utils.get(ctx.guild.roles, name=course)
            if role is None:
                missing.add(course)
            else:
                course_roles[course] = role

        if missing:
            await ctx.response.send_message(embed=error_embed(
                'Missing the following roles: ```\n'
                + '\n'.join(sorted(missing)) + '\n```'))
            return

        await ctx.response.defer(ephemeral=True)

        with capture_logs(logger) as logs:
            created_channels: set[str] = set()
            for area, levels in COURSES.items():
                if not isinstance(area, int):
                    continue # don't create minor/cert channels by default
                courses = [course for level in levels.values()
                           for course in level]
                # concatenating levels puts things out of order
                courses.sort()
                for course in courses:
                    _, created = await add_course(ctx.guild, area, course, False)
                    created_channels.update({ch.name for ch in created})
        await ctx.edit_original_response(
            content=tail(logs, '```\n{}\n```\nDone.'))

    @app_commands.command()
    async def roles(self, ctx: discord.Interaction) -> None:
        """Set up area and course roles."""
        assert ctx.guild is not None
        await ctx.response.defer(ephemeral=True)

        async def make_role(name: str) -> None:
            assert ctx.guild is not None
            await ctx.guild.create_role(
                name=name, permissions=discord.Permissions.none(),
                hoist=False, mentionable=False)

        with capture_logs(logger) as logs:
            for area in range(1, 9):
                name = f'Area {area}'
                role = discord.utils.get(ctx.guild.roles, name=name)
                if role is None:
                    logger.debug('Creating missing %r role', name)
                    await make_role(name)
                else:
                    logger.debug('%r role already exists', name)

            courses = {course for area, levels in COURSES.items()
                       if isinstance(area, int)
                       for level in levels.values() for course in level}
            for course in courses:
                role = discord.utils.get(ctx.guild.roles, name=course)
                if role is None:
                    logger.debug('Creating missing role for %s', course)
                    await make_role(course)
                else:
                    logger.debug('%s role already exists', course)

        await ctx.edit_original_response(
            content=tail(logs, '```\n{}\n```\nDone.'))

    @app_commands.command()
    @app_commands.describe(
        course='The course to set up.',
        on_demand='If True, create channels only '
        'if configured to do so on demand.',
    )
    async def course(self, ctx: discord.Interaction,
                     course: str, on_demand: bool = False) -> None:
        """Set up the role and channels for one course."""
        assert ctx.guild is not None
        await ctx.response.defer()

        amc = course_amc(course)

        # ensure the course exists
        courses = {course for area, levels in COURSES.items() if area == amc
                   for courses in levels.values() for course in courses}
        if course not in courses:
            await ctx.edit_original_response(embed=error_embed(
                f'No such course: {course!r}'
            ))
            return

        await add_course(ctx.guild, amc, course, on_demand)
        await ctx.edit_original_response(
            content=f'Successfully created {course!r} role/channels')

    @course.autocomplete('course')
    async def course_autocomplete(self, ctx: discord.Interaction,
                                  value: str) -> list[app_commands.Choice]:
        return await course_complete(ctx, value)

class Teardown(app_commands.Group):

    def __init__(self) -> None:
        super().__init__(
            name='teardown',
            description='Tear down items, to set them up again',
            guild_only=True,
            default_permissions=discord.Permissions.none(),
        )

    @app_commands.command()
    @app_commands.describe(cat='The category to tear down.')
    async def category(self, ctx: discord.Interaction,
                       cat: discord.CategoryChannel) -> None:
        """Tear down a category and all its subchannels."""
        await ctx.response.defer()
        for channel in cat.channels:
            logger.debug('Deleting #%s', channel.name)
            await channel.delete()
        logger.debug('Deleting category %r', cat.name)
        await cat.delete()
        await ctx.edit_original_response(
            content=f'Deleted {cat.name!r} and its members.')

    @app_commands.command()
    @app_commands.describe(pattern='Python-flavored regex pattern. Roles with '
                           'names matching this pattern will be deleted.')
    async def roles(self, ctx: discord.Interaction, pattern: str) -> None:
        """Tear down all roles matching a regex."""
        assert ctx.guild is not None
        await ctx.response.defer()
        deleted: list[str] = []
        for role in ctx.guild.roles:
            if re.search(pattern, role.name):
                logger.debug('Deleting role %r', role.name)
                await role.delete()
                deleted.append(role.name)
        await ctx.edit_original_response(
            content='Deleted: ```\n' + '\n'.join(deleted) + '\n```')

def setup(bot: commands.Bot) -> None:
    bot.tree.add_command(Setup())
    bot.tree.add_command(Teardown())
