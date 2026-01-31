from prompt_toolkit import PromptSession
from prompt_toolkit.shortcuts import CompleteStyle
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.styles.pygments import style_from_pygments_cls
from pygments.styles import get_style_by_name
from .shell_lexer import ShellLexer
from .completer import ShellCompleter
from ..core import is_python_code_complete, get_auto_indent


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


def create_prompt_session(builtin_commands=None):
    """Create and configure a PromptSession for the shell."""
    style = style_from_pygments_cls(get_style_by_name('dracula'))
    completer = ShellCompleter(builtin_commands)
    return PromptSession(
        lexer=PygmentsLexer(ShellLexer),
        style=style,
        multiline=True,
        key_bindings=create_key_bindings(),
        completer=completer,
        complete_style=CompleteStyle.MULTI_COLUMN,
        complete_in_thread=True,
        enable_history_search=True,
    )
