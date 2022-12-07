from typing import Optional

# If running in a specific guild, set this to its ID.
# Otherwise, use None.
DEBUG_GUILD: Optional[int]
# The Discord bot application token
TOKEN: str
# The log level to emit, e.g. logging.DEBUG
LOG_LEVEL: int # logging.*
# If True, logs will be emitted to standard output
# instead of to a timestamped file.
LOG_TO_STDOUT: bool
# An URL to give server admins to invite the bot.
# Set to None to disable the /invite command.
INVITE_URL: Optional[str]
# The Unix timestamp past which global commands are considered up-to-date.
# The bot will sync global commands if this is in the future. Set this to be
# far in the future if you expect to be changing command signatures often;
# otherwise put it a minute or so ahead if you need to sync.
# The bot will always sync guild commands if DEBUG_GUILD is set.
COMMAND_FRESHNESS: float
