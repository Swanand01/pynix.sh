import os
import re
import shutil
from keyword import iskeyword
from pygments.lexer import include, inherit
from pygments.lexers.python import Python3Lexer
from pygments.token import (
    Name,
    Operator,
    Punctuation,
    String,
    Text,
    Whitespace,
)

COMMAND_TOKEN_RE = r'[^=\s\[\]{}()$"\'`<&|;!]+(?=\s|$|\)|\]|\}|!)'


def is_valid_command(cmd):
    """Check if command exists in PATH and is not a Python keyword."""
    return not iskeyword(cmd) and shutil.which(cmd) is not None


def is_valid_path(path):
    """Check if path exists."""
    try:
        return os.path.exists(os.path.expanduser(path))
    except (OSError, ValueError):
        return False


def subproc_cmd_callback(_, match):
    """Yield Name.Builtin if command exists, otherwise Text."""
    cmd = match.group()
    yield match.start(), Name.Builtin if is_valid_command(cmd) else Text, cmd


def subproc_arg_callback(_, match):
    """Check if match contains a valid path and highlight it."""
    text = match.group()
    token = String if is_valid_path(text) else Text
    yield match.start(), token, text


class ShellLexer(Python3Lexer):
    """
    Custom lexer that extends Python3Lexer with shell syntax highlighting.
    Dynamically highlights commands and paths.
    """

    name = 'ShellLexer'
    aliases = ['shell']

    tokens = {
        'root': [
            # Redirection and pipe operators
            (r'>>', Operator),
            (r'[|<>&;]', Operator),

            # Environment variables
            (r'\$\w+', Name.Variable),

            # Opening brackets/parens for Python code
            (r'\(', Punctuation, 'py_bracket'),
            (r'\{', Punctuation, 'py_curly_bracket'),

            # Inherit all Python tokens
            inherit,
        ],
        'py_bracket': [(r'\)', Punctuation, '#pop'), include('root')],
        'py_curly_bracket': [(r'\}', Punctuation, '#pop'), include('root')],
        'subproc_start': [
            (r'\s+', Whitespace),
            (COMMAND_TOKEN_RE, subproc_cmd_callback, '#pop'),
            (r'', Whitespace, '#pop'),
        ],
        'subproc': [
            (r'&&|\|\|', Operator, 'subproc_start'),
            (r'"(\\\\|\\[0-7]+|\\.|[^"\\])*"', String.Double),
            (r"'(\\\\|\\[0-7]+|\\.|[^'\\])*'", String.Single),
            (r';', Punctuation, 'subproc_start'),
            (r'[&=]', Punctuation),
            (r'\|', Punctuation, 'subproc_start'),
            (r'\s+', Text),
            (r'[^=\s\[\]{}()$"\'`<&|;]+', subproc_arg_callback),
            (r'<|>', Text),
            (r'\$\w+', Name.Variable),
        ],
    }

    def get_tokens_unprocessed(self, text, **_):
        """Check first token - if it's a valid command, enter subproc mode."""
        start = 0
        state = ('root',)

        # Check if line starts with a command
        m = re.match(rf'(\s*)({COMMAND_TOKEN_RE})', text)
        if m is not None:
            yield m.start(1), Whitespace, m.group(1)
            start = m.end(1)
            cmd = m.group(2)

            # Check if it's a valid shell command (not a Python keyword)
            if is_valid_command(cmd):
                yield m.start(2), Name.Builtin, cmd
                start = m.end(2)
                state = ('subproc',)

        # Process the rest with either Python or shell highlighting
        for i, t, v in super().get_tokens_unprocessed(text[start:], state):
            yield i + start, t, v
