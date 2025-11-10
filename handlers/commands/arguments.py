"""Command argument definition and parsing system."""

import re
import html
from typing import Any, Dict, List, Optional, Union, Callable
from enum import Enum
from dataclasses import dataclass


class ArgumentType(Enum):
    """Types of command arguments."""
    STRING = "string"
    INTEGER = "int"
    FLOAT = "float"
    BOOLEAN = "bool"
    CHOICE = "choice"
    FLAG = "flag"  # Simple presence/absence flag


@dataclass
class ArgumentDefinition:
    """Definition of a command argument."""
    name: str
    type: ArgumentType
    required: bool = False
    default: Any = None
    description: str = ""
    choices: Optional[List[str]] = None  # For CHOICE type
    min_value: Optional[Union[int, float]] = None  # For INTEGER/FLOAT types
    max_value: Optional[Union[int, float]] = None  # For INTEGER/FLOAT types
    validator: Optional[Callable[[Any], bool]] = None  # Custom validation function

    def __post_init__(self):
        """Validate argument definition after initialization."""
        if self.type == ArgumentType.CHOICE and not self.choices:
            raise ValueError(f"Argument '{self.name}' of type CHOICE must have choices defined")

        if self.type in [ArgumentType.INTEGER, ArgumentType.FLOAT]:
            if self.min_value is not None and self.max_value is not None and self.min_value > self.max_value:
                raise ValueError(f"Argument '{self.name}': min_value cannot be greater than max_value")


class ArgumentParseError(Exception):
    """Exception raised when argument parsing fails."""
    pass


class ParsedArguments:
    """Container for parsed command arguments."""

    def __init__(self, args_dict: Dict[str, Any]):
        """Initialize with parsed arguments dictionary."""
        self._args = args_dict.copy()

    def get(self, name: str, default: Any = None) -> Any:
        """Get argument value by name."""
        return self._args.get(name, default)

    def __getitem__(self, name: str) -> Any:
        """Get argument value by name."""
        return self._args[name]

    def __contains__(self, name: str) -> bool:
        """Check if argument exists."""
        return name in self._args

    def __iter__(self):
        """Iterate over argument names."""
        return iter(self._args)

    def items(self):
        """Get items as (name, value) pairs."""
        return self._args.items()

    def keys(self):
        """Get argument names."""
        return self._args.keys()

    def values(self):
        """Get argument values."""
        return self._args.values()


class ArgumentParser:
    """Parser for command arguments based on definitions."""

    def __init__(self, definitions: List[ArgumentDefinition]):
        """Initialize parser with argument definitions."""
        self.definitions = definitions
        self._arg_map = {arg.name: arg for arg in definitions}

    def parse(self, args_string: str) -> ParsedArguments:
        """Parse arguments from string.

        Args:
            args_string: String containing arguments (e.g., "arg1 value1 arg2 value2")

        Returns:
            ParsedArguments object with parsed values

        Raises:
            ArgumentParseError: If parsing fails
        """
        if not args_string.strip():
            # No arguments provided
            return self._parse_empty_args()

        # Split arguments, handling quoted strings
        args_parts = self._split_arguments(args_string.strip())

        # Parse positional and named arguments
        parsed = {}
        positional_defs = [arg for arg in self.definitions if not arg.name.startswith('-')]
        named_defs = {arg.name: arg for arg in self.definitions if arg.name.startswith('-')}

        i = 0
        while i < len(args_parts):
            part = args_parts[i]

            if part.startswith('-') and part in named_defs:
                # Named argument
                arg_def = named_defs[part]
                if i + 1 >= len(args_parts):
                    raise ArgumentParseError(f"Missing value for argument '{part}'")
                value_str = args_parts[i + 1]
                parsed[arg_def.name] = self._parse_value(value_str, arg_def)
                i += 2
            elif i < len(positional_defs):
                # Positional argument
                arg_def = positional_defs[i]
                if arg_def.type == ArgumentType.STRING and i == len(positional_defs) - 1:
                    # For the last positional string argument, take the rest of the input
                    value_str = ' '.join(args_parts[i:])
                    parsed[arg_def.name] = self._parse_value(value_str, arg_def)
                    i = len(args_parts)
                else:
                    # Regular positional argument
                    parsed[arg_def.name] = self._parse_value(part, arg_def)
                    i += 1
            else:
                raise ArgumentParseError(f"Unexpected argument: {part}")

        # Add defaults for missing optional arguments
        for arg_def in self.definitions:
            if arg_def.name not in parsed:
                if arg_def.required:
                    raise ArgumentParseError(f"Missing required argument: {arg_def.name}")
                elif arg_def.default is not None:
                    parsed[arg_def.name] = arg_def.default

        # Validate all parsed arguments
        for name, value in parsed.items():
            arg_def = self._arg_map[name]
            if not self._validate_value(value, arg_def):
                raise ArgumentParseError(f"Invalid value for argument '{name}': {value}")

        return ParsedArguments(parsed)

    def _parse_empty_args(self) -> ParsedArguments:
        """Handle case where no arguments are provided."""
        parsed = {}
        for arg_def in self.definitions:
            if arg_def.required:
                raise ArgumentParseError(f"Missing required argument: {arg_def.name}")
            elif arg_def.default is not None:
                parsed[arg_def.name] = arg_def.default
        return ParsedArguments(parsed)

    def _split_arguments(self, args_string: str) -> List[str]:
        """Split argument string handling quotes."""
        # Simple quote-aware splitting
        parts = []
        current = ""
        in_quotes = False
        quote_char = None

        for char in args_string:
            if not in_quotes and char in ('"', "'"):
                in_quotes = True
                quote_char = char
            elif in_quotes and char == quote_char:
                in_quotes = False
                quote_char = None
            elif not in_quotes and char.isspace():
                if current:
                    parts.append(current)
                    current = ""
            else:
                current += char

        if current:
            parts.append(current)

        if in_quotes:
            raise ArgumentParseError("Unclosed quote in arguments")

        return parts

    def _parse_value(self, value_str: str, arg_def: ArgumentDefinition) -> Any:
        """Parse string value according to argument type."""
        try:
            if arg_def.type == ArgumentType.STRING:
                return value_str
            elif arg_def.type == ArgumentType.INTEGER:
                return int(value_str)
            elif arg_def.type == ArgumentType.FLOAT:
                return float(value_str)
            elif arg_def.type == ArgumentType.BOOLEAN:
                return value_str.lower() in ('true', '1', 'yes', 'on')
            elif arg_def.type == ArgumentType.CHOICE:
                if value_str not in arg_def.choices:
                    raise ValueError(f"Value must be one of: {', '.join(arg_def.choices)}")
                return value_str
            elif arg_def.type == ArgumentType.FLAG:
                return True  # Presence of flag means True
            else:
                raise ValueError(f"Unsupported argument type: {arg_def.type}")
        except ValueError as e:
            raise ArgumentParseError(f"Invalid value for {arg_def.type.value} argument '{arg_def.name}': {e}")

    def _validate_value(self, value: Any, arg_def: ArgumentDefinition) -> bool:
        """Validate parsed value against argument definition."""
        if arg_def.validator:
            return arg_def.validator(value)

        if arg_def.type == ArgumentType.INTEGER:
            if not isinstance(value, int):
                return False
            if arg_def.min_value is not None and value < arg_def.min_value:
                return False
            if arg_def.max_value is not None and value > arg_def.max_value:
                return False
        elif arg_def.type == ArgumentType.FLOAT:
            if not isinstance(value, (int, float)):
                return False
            if arg_def.min_value is not None and value < arg_def.min_value:
                return False
            if arg_def.max_value is not None and value > arg_def.max_value:
                return False

        return True

    def generate_help_text(self, language: str = "en") -> str:
        """Generate help text from argument definitions."""
        if not self.definitions:
            return "No arguments required."

        lines = []
        required_args = [arg for arg in self.definitions if arg.required]
        optional_args = [arg for arg in self.definitions if not arg.required]

        if required_args:
            lines.append("Required arguments:")
            for arg in required_args:
                lines.append(self._format_argument_help(arg, language))

        if optional_args:
            if required_args:
                lines.append("")
            lines.append("Optional arguments:")
            for arg in optional_args:
                lines.append(self._format_argument_help(arg, language))

        # Escape HTML entities for safe HTML display
        help_text = "\n".join(lines)
        return self._escape_html(help_text)

    def _format_argument_help(self, arg_def: ArgumentDefinition, language: str) -> str:
        """Format help text for a single argument."""
        name = arg_def.name
        desc = arg_def.description or "No description"

        if arg_def.type == ArgumentType.CHOICE:
            choices_text = f" (choices: {', '.join(arg_def.choices)})"
        elif arg_def.type in [ArgumentType.INTEGER, ArgumentType.FLOAT]:
            range_parts = []
            if arg_def.min_value is not None:
                range_parts.append(f"min: {arg_def.min_value}")
            if arg_def.max_value is not None:
                range_parts.append(f"max: {arg_def.max_value}")
            range_text = f" ({', '.join(range_parts)})" if range_parts else ""
        else:
            range_text = ""

        default_text = f" [default: {arg_def.default}]" if arg_def.default is not None else ""

        return f"  {name}: {desc}{range_text}{default_text}"

    def _escape_html(self, text: str) -> str:
        """Escape HTML entities for safe HTML display."""
        return html.escape(text, quote=True)
