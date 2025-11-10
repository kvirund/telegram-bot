"""Command handlers package.

This package contains all bot commands and the command registry system.
Commands are automatically registered when this package is imported.
"""

# Import registry first to ensure it exists
from .registry import command_registry

# Import command modules to register them
# Core user commands
from . import help_command
from . import joke_command
from . import ask_command

# Admin commands
from . import reload_command
from . import context_command
from . import profile_command
from . import chats_command
from . import setprompt_command
from . import saveprofiles_command
from . import comment_command

# Additional commands
from . import reactionstats_command
from . import groupmood_command

__all__ = [
    'command_registry',
]
