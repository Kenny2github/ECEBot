# stdlib
import re
from logging import getLogger

# 3rd-party
import discord
from discord.ext import commands
from discord import app_commands

# 1st-party
from ..controller.role_assignment import COURSES
from ..logs import capture_logs
from ..utils import error_embed

logger = getLogger(__name__)

COURSE_CHANNEL_SUFFIXES = ['', '-hw-help']

def tail(logs: list[str], format: str) -> str:
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
        for area in range(1, 8):
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
            default_perms = discord.PermissionOverwrite(read_messages=False)
            role_perms = discord.PermissionOverwrite(read_messages=True)
            my_perms = discord.PermissionOverwrite(
                read_messages=True, manage_permissions=True,
                manage_roles=True, manage_channels=True)
            created_channels: set[str] = set()
            for area, levels in COURSES.items():
                courses = [course for level in levels.values()
                           for course in level]
                # concatenating levels puts things out of order
                courses.sort()
                name = f'Area {area}'
                cat = discord.utils.get(ctx.guild.categories, name=name)
                if cat is None:
                    logger.debug('Creating %r category', name)
                    cat = await ctx.guild.create_category(name, overwrites={
                        ctx.guild.default_role: default_perms,
                        area_roles[area]: role_perms,
                        ctx.guild.me: my_perms,
                    })
                else:
                    logger.debug('Found %r category', name)
                for course in courses:
                    for suffix in COURSE_CHANNEL_SUFFIXES:
                        name = course.lower() + suffix
                        if name in created_channels:
                            logger.debug('Already created/found #%s', name)
                            continue
                        channel = discord.utils.get(cat.channels, name=name)
                        if channel is not None:
                            logger.debug('Found #%s', name)
                            created_channels.add(name)
                            continue
                        logger.debug('Creating #%s', name)
                        await cat.create_text_channel(name, overwrites={
                            ctx.guild.default_role: default_perms,
                            # for potential area reps
                            area_roles[area]: role_perms,
                            course_roles[course]: role_perms,
                            ctx.guild.me: my_perms,
                        })
                        created_channels.add(name)
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
            for area in range(1, 8):
                name = f'Area {area}'
                role = discord.utils.get(ctx.guild.roles, name=name)
                if role is None:
                    logger.debug('Creating missing %r role', name)
                    await make_role(name)
                else:
                    logger.debug('%r role already exists', name)

            courses = {course for area in COURSES.values()
                    for level in area.values() for course in level}
            for course in courses:
                role = discord.utils.get(ctx.guild.roles, name=course)
                if role is None:
                    logger.debug('Creating missing role for %s', course)
                    await make_role(course)
                else:
                    logger.debug('%s role already exists', course)

        await ctx.edit_original_response(
            content=tail(logs, '```\n{}\n```\nDone.'))

class Teardown(app_commands.Group):

    def __init__(self) -> None:
        super().__init__(
            name='teardown',
            description='Tear down items, to set them up again',
            guild_only=True,
            default_permissions=discord.Permissions.none(),
        )

    @app_commands.command()
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
