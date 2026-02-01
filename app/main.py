from .core import run_command
from .types import Command
from .commands.builtins import HISTFILE
from .ui import create_prompt_session, get_prompt


def main():
    """Main REPL loop for the shell."""
    builtin_commands = [c.value for c in Command]
    session = create_prompt_session(builtin_commands, histfile=HISTFILE)

    while True:
        try:
            command = session.prompt(get_prompt()).strip()
        except KeyboardInterrupt:
            continue
        except EOFError:
            break

        if command and run_command(command):
            break


if __name__ == "__main__":
    main()
