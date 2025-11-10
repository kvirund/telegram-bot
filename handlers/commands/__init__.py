"""Command handlers package.

This package contains all bot commands and the command registry system.
Commands are automatically registered when this package is imported.
"""

# Import registry first to ensure it exists
from .registry import command_registry

# Import command modules to register them
# Core user commands
from . import help_command  # noqa: F401
from . import joke_command  # noqa: F401
from . import ask_command  # noqa: F401

# Admin commands
from . import reload_command  # noqa: F401
from . import context_command  # noqa: F401
from . import profile_command  # noqa: F401
from . import chats_command  # noqa: F401
from . import setprompt_command  # noqa: F401
from . import saveprofiles_command  # noqa: F401
from . import comment_command  # noqa: F401

# Additional commands
from . import reactionstats_command  # noqa: F401
from . import groupmood_command  # noqa: F401

__all__ = [
    "command_registry",
]
