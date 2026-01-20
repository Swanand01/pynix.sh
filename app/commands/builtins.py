import os
import sys
from enum import Enum
from pathlib import Path
from ..utils import file_exists_in_path


class Command(str, Enum):
    EXIT = 'exit'
    ECHO = 'echo'
    TYPE = 'type'
    PWD = 'pwd'
    CD = 'cd'


command_docs = {
    Command.EXIT: {
        "description": "Exit the shell",
        "usage": "exit",
    },
    Command.ECHO: {
        "description": "Prints the provided arguments",
        "usage": "echo [args...]"
    },
    Command.TYPE: {
        "description": "Displays the type of the provided argument",
        "usage": "type [arg]"
    },
    Command.PWD: {
        "description": "Prints the current working directory",
        "usage": "pwd"
    },
    Command.CD: {
        "description": "Changes the current directory",
        "usage": "cd [directory]"
    },
}


def command_exists(command):
    """Check if a command is a shell builtin."""
    return command in list(Command)


def handle_echo_command(args):
    """Handle the echo builtin command."""
    print(' '.join(args))


def handle_type_command(arg):
    """Handle the type builtin command."""
    if command_exists(arg):
        print(f"{arg} is a shell builtin")
        return

    file_exists, file_path = file_exists_in_path(arg)
    if not file_exists:
        print(f"{arg}: not found")
        return

    print(f"{arg} is {file_path}")


def handle_pwd_command():
    """Handle the pwd builtin command."""
    print(os.getcwd())


def handle_cd_command(arg):
    """Handle the cd builtin command."""
    if arg == "~":
        arg = str(Path.home())
        os.chdir(arg)
        return

    if not os.path.isdir(arg):
        sys.stderr.write(f"cd: {arg}: No such file or directory\n")
        return

    os.chdir(arg)


def handle_builtin_command(cmd, args):
    """
    Execute a builtin command.

    Returns:
        True if command was 'exit', False otherwise
    """
    if cmd == Command.EXIT:
        return True
    elif cmd == Command.ECHO:
        handle_echo_command(args)
    elif cmd == Command.TYPE:
        if args:
            handle_type_command(args[0])
    elif cmd == Command.PWD:
        handle_pwd_command()
    elif cmd == Command.CD:
        if args:
            handle_cd_command(args[0])

    return False
