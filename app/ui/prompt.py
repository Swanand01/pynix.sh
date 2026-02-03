import code
import os
import sys
import socket
from pathlib import Path
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.styles.pygments import style_from_pygments_cls
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from pygments.styles import get_style_by_name
from .shell_lexer import ShellLexer
from .completer import ShellCompleter


# Cache for static prompt parts
_prompt_cache = {}


def get_venv_name():
    """Detect active virtual environment name."""
    venv_path = os.environ.get('VIRTUAL_ENV')
    if venv_path:
        return Path(venv_path).name

    conda_env = os.environ.get('CONDA_DEFAULT_ENV')
    if conda_env and conda_env != 'base':
        return conda_env

    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        return Path(sys.prefix).name

    return None


def is_python_code_complete(text):
    """Check if Python code is complete and ready to execute."""
    try:
        return code.compile_command(text) is not None
    except SyntaxError:
        return True


def get_auto_indent(text):
    """Calculate auto-indent for Python code based on the last line."""
    for line in reversed(text.split('\n')):
        if line.strip():
            indent = len(line) - len(line.lstrip())
            if line.rstrip().endswith(':'):
                return ' ' * (indent + 4)
            return ' ' * indent
    return ''


def get_prompt():
    """Build the shell prompt text."""
    if 'user' not in _prompt_cache:
        _prompt_cache['user'] = os.environ.get(
            "USER") or os.environ.get("USERNAME") or ""
        _prompt_cache['host'] = socket.gethostname()
        _prompt_cache['home'] = str(Path.home())

    user = _prompt_cache['user']
    host = _prompt_cache['host']
    home = _prompt_cache['home']

    cwd = os.getcwd()
    prompt_dir = cwd.replace(home, "~") if cwd.startswith(home) else cwd

    # Build prompt parts
    prompt_parts = []

    # Add venv name if active
    venv = get_venv_name()
    if venv:
        prompt_parts.extend([
            ('class:pygments.comment', '('),
            ('class:pygments.name.decorator', venv),
            ('class:pygments.comment', ') '),
        ])

    # Add user@host and directory
    prompt_parts.extend([
        ('class:pygments.name.function', user),
        ('class:pygments.operator', '@'),
        ('class:pygments.name.class', f"{host} "),
        ('class:pygments.literal.string', prompt_dir),
        ('class:pygments.operator', ' > '),
    ])

    return FormattedText(prompt_parts)


def create_key_bindings():
    """Create key bindings for the shell prompt."""
    bindings = KeyBindings()

    @bindings.add(Keys.Enter)
    def _(event):
        """Handle Enter with auto-indentation for Python code (xonsh-style)."""
        buffer = event.current_buffer
        text = buffer.text
        current_line = buffer.document.current_line

        # If current line is empty/whitespace, accept input (double-enter behavior)
        if not current_line.strip():
            buffer.validate_and_handle()
            return

        # Check if Python code is complete
        if not is_python_code_complete(text):
            # Code is incomplete, add newline with auto-indent
            buffer.insert_text('\n')
            auto_indent = get_auto_indent(text)
            if auto_indent:
                buffer.insert_text(auto_indent)
            return

        # Code is complete (or has syntax error), accept input
        buffer.validate_and_handle()

    return bindings


def create_prompt_session(builtin_commands=None, histfile=None):
    """Create and configure a PromptSession for the shell."""
    style = style_from_pygments_cls(get_style_by_name('dracula'))
    completer = ShellCompleter(builtin_commands)
    history = FileHistory(histfile) if histfile else None

    return PromptSession(
        lexer=PygmentsLexer(ShellLexer),
        style=style,
        multiline=True,
        key_bindings=create_key_bindings(),
        completer=completer,
        complete_style=CompleteStyle.MULTI_COLUMN,
        complete_in_thread=True,
        enable_history_search=True,
        auto_suggest=AutoSuggestFromHistory(),
        history=history,
    )
