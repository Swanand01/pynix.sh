import os
import sys
import socket
from pathlib import Path
from prompt_toolkit.formatted_text import FormattedText
from .core import execute_python, execute_external, is_python_code
from .core.execution import has_substitution
from .parsing import parse_pipeline
from .parsing.pipeline import execute_pipeline
from .types import Command, is_builtin
from .commands import execute_builtin
from .commands.builtins import HISTFILE
from .ui import create_prompt_session


def main():
    """Main REPL loop for the shell."""
    home = str(Path.home())
    builtin_commands = [c.value for c in Command]
    session = create_prompt_session(builtin_commands, histfile=HISTFILE)

    user = os.environ.get("USER") or os.environ.get("USERNAME") or ""
    host = socket.gethostname()

    while True:
        cwd = os.getcwd()
        prompt_dir = cwd.replace(home, "~") if cwd.startswith(home) else cwd

        try:
            prompt_text = FormattedText([
                ('class:pygments.name.function', f"{user}"),
                ('class:pygments.operator', '@'),
                ('class:pygments.name.class', f"{host} "),
                ('class:pygments.literal.string', prompt_dir),
                ('class:pygments.operator', ' > '),
            ])
            command = session.prompt(prompt_text).strip()
        except KeyboardInterrupt:
            continue
        except EOFError:
            break

        if not command:
            continue

        # Handle $() and !() substitutions before pipeline parsing
        if has_substitution(command):
            execute_python(command)
            continue

        # Parse command into pipeline segments
        pipeline = parse_pipeline(command)

        # Handle pipelines
        if len(pipeline) > 1:
            execute_pipeline(pipeline)
            continue

        # Single command
        segment = pipeline[0]
        cmd = segment['parts'][0] if segment['parts'] else None

        # Handle builtin
        if is_builtin(cmd):
            should_exit = execute_builtin(segment)
            if should_exit:
                break
            continue

        # Execute as Python code if it compiles as Python
        if is_python_code(command):
            execute_python(command)
            continue

        # Execute as external command
        if not execute_external(segment):
            print(f"{cmd}: command not found", file=sys.stderr)


if __name__ == "__main__":
    main()
