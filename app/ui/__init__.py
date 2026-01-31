"""User interface components - prompt session and syntax highlighting."""
from .prompt import create_prompt_session
from .shell_lexer import ShellLexer

__all__ = [
    'create_prompt_session',
    'ShellLexer',
]
