"""
Python namespace management for the unified shell.
"""

from ...types import CommandResult


# Persistent namespace for Python code execution
python_namespace = {
    '__name__': '__main__',
    '__builtins__': __builtins__,
    'CommandResult': CommandResult,
}


def get_namespace():
    """Get the shared Python namespace."""
    return python_namespace


def initialize_namespace(expand_at, shell):
    """
    Initialize namespace with runtime functions.

    Args:
        expand_at: @() formatting function
        shell: Unified shell execution function (handles $(), !(), and plain commands)
    """
    python_namespace['__expand_at'] = expand_at
    python_namespace['__shell'] = shell
