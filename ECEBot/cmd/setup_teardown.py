# stdlib
import re
from logging import getLogger

# 3rd-party
import discord
from discord.ext import commands
from discord import app_commands

# 1st-party
from ..controller.role_assignment import COURSES
from ..utils import error_embed

logger = getLogger(__name__)

class Setup(app_commands.Group):

    def __init__(self) -> None:
        super().__init__(
            name='setup',
            description='Perform server setup tasks',
            guild_only=True,
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

        default_perms = discord.PermissionOverwrite(read_messages=False)
        role_perms = discord.PermissionOverwrite(read_messages=True)
        my_perms = discord.PermissionOverwrite(
            read_messages=True, manage_permissions=True,
            manage_roles=True, manage_channels=True)
        created_courses: set[str] = set()
        for area, levels in COURSES.items():
            courses = [course for level in levels.values() for course in level]
            name = f'Area {area}'
            logger.debug('Creating %r category', name)
            cat = await ctx.guild.create_category(name, overwrites={
                ctx.guild.default_role: default_perms,
                area_roles[area]: role_perms,
                ctx.guild.me: my_perms,
            })
            for course in courses:
                if course in created_courses:
                    logger.debug('Already created a channel for %s', course)
                    continue
                name = course.lower()
                logger.debug('Creating #%s', name)
                await cat.create_text_channel(name, overwrites={
                    ctx.guild.default_role: default_perms,
                    area_roles[area]: role_perms, # for potential area reps
                    course_roles[course]: role_perms,
                    ctx.guild.me: my_perms,
                })
                created_courses.add(course)
        await ctx.edit_original_response(content='Done.')

    @app_commands.command()
    async def roles(self, ctx: discord.Interaction) -> None:
        """Set up area and course roles."""
        assert ctx.guild is not None
        await ctx.response.defer()

        async def make_role(name: str) -> None:
            assert ctx.guild is not None
            await ctx.guild.create_role(
                name=name, permissions=discord.Permissions.none(),
                hoist=False, mentionable=False)

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

        await ctx.edit_original_response(content='Done.')

class Teardown(app_commands.Group):

    def __init__(self) -> None:
        super().__init__(
            name='teardown',
            description='Tear down items, to set them up again',
            guild_only=True,
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
