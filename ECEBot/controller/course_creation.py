# stdlib
import re
import tomllib
from collections import defaultdict
from typing import Optional, TypedDict, cast
from logging import getLogger

# 3rd-party
import discord

# 1st-party
from ..utils import Category, Level

logger = getLogger(__name__)

COURSE_CHANNEL_SUFFIXES = ['', '-hw-help']
COURSES_FILENAME = 'courses.toml'

class CourseCategory(TypedDict):
    name: str
    courses: list[str]

# load course info

AREAS: dict[int, str] = {}
MINORS_CERTS: dict[str, str] = {}
COURSES: dict[Category, defaultdict[Level, list[str]]] = {}

def load_course_info():
    with open(COURSES_FILENAME, 'rb') as f:
        courses: dict[str, CourseCategory] = tomllib.load(f)

    for key, value in courses.items():
        if key.startswith('area-'):
            category = int(key[len('area-'):])
            AREAS[category] = value['name']
        else:
            category = key
            MINORS_CERTS[category] = value['name']
        COURSES[category] = defaultdict(list)
        for course in value['courses']:
            code = re.search(r'[A-Z]{3}([12345ABCD])\d\d', course)
            if code is None:
                raise ValueError(f'Invalid course code {course!r}')
            code = code.group(1)
            if code.isnumeric():
                level = cast(Level, int(code) * 100)
            else: # UTSC-style ABCD level
                level = cast(Level, (ord(code) - ord('A') + 1) * 100)
            COURSES[category][level].append(course)
        for course_list in COURSES[category].values():
            course_list.sort()

# end course info

# For the following functions, "amc" is an abbreviation for "area/minor/certificate".

def amc_name(amc: Category) -> str:
    """Get a string name for an area/minor/certificate."""
    if isinstance(amc, int):
        amc = f'Area {amc}'
    return amc

def course_amc(course: str) -> Category:
    """Get an area/minor/certificate that a course belongs to."""
    for area, levels in COURSES.items():
        for level in levels.values():
            if course in level:
                return area
    raise ValueError(course)

def amc_role(guild: discord.Guild,
             amc: Category) -> Optional[discord.Role]:
    """Get a role for an area/minor/certificate, or None if not found."""
    return discord.utils.get(guild.roles, name=amc_name(amc))

def amc_category(guild: discord.Guild,
                 amc: Category) -> Optional[discord.CategoryChannel]:
    """Get a category for an area/minor/certificate, or None if not found."""
    return discord.utils.get(guild.categories, name=amc_name(amc))

def course_role(guild: discord.Guild, course: str) -> Optional[discord.Role]:
    """Get a role for a course, or None if not found."""
    return discord.utils.get(guild.roles, name=course)

async def add_course(guild: discord.Guild, amc: Category,
                     course: str) -> tuple[discord.Role, list[discord.TextChannel]]:
    """Create a role+category+channel set for a course."""
    amc = amc_name(amc)
    _amc_role = amc_role(guild, amc)
    assert _amc_role is not None
    # define perms for various contexts
    default_perms = discord.PermissionOverwrite(read_messages=False)
    role_perms = discord.PermissionOverwrite(read_messages=True)
    my_perms = discord.PermissionOverwrite(
        read_messages=True, manage_permissions=True,
        manage_roles=True, manage_channels=True,
    )
    # get role for course
    role = course_role(guild, course)
    if role is None:
        logger.debug('Creating %r role', course)
        role = await guild.create_role(
            name=course, permissions=discord.Permissions.none(),
            hoist=False, mentionable=False
        )
    # get a/m/c category
    category = amc_category(guild, amc)
    if category is None:
        logger.debug('Creating %r category', amc)
        category = await guild.create_category(amc, overwrites={
            guild.default_role: default_perms,
            _amc_role: role_perms,
            guild.me: my_perms,
        })
    # create channels
    channels: list[discord.TextChannel] = []
    for suffix in COURSE_CHANNEL_SUFFIXES:
        name = course.lower() + suffix
        channel = discord.utils.get(category.channels, name=name)
        if channel is not None:
            logger.debug('Found #%s', name)
            continue
        logger.debug('Creating #%s', name)
        channel = await category.create_text_channel(name, overwrites={
            guild.default_role: default_perms,
            # for potential area reps
            _amc_role: role_perms,
            role: role_perms,
            guild.me: my_perms,
        })
    return role, channels
