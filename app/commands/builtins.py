import os
import sys
from enum import Enum
from pathlib import Path
from ..utils import executable_exists_in_path
from ..redirection import redirect_stdout, restore_stdout, redirect_stderr, restore_stderr, parse_segment
from .history import command_history, load_history_from_file, append_history_to_file, write_history_to_file


class Command(str, Enum):
    EXIT = 'exit'
    ECHO = 'echo'
    TYPE = 'type'
    PWD = 'pwd'
    CD = 'cd'
    HISTORY = 'history'


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
    Command.HISTORY: {
        "description": "Displays the command history",
        "usage": "history"
    },
}


def is_builtin(command):
    """Check if a command is a shell builtin."""
    return command in list(Command)


def handle_echo(args):
    """Handle the echo builtin command."""
    print(' '.join(args))


def handle_type(arg):
    """Handle the type builtin command."""
    if is_builtin(arg):
        print(f"{arg} is a shell builtin")
        return

    executable_exists, executable_path = executable_exists_in_path(arg)
    if not executable_exists:
        print(f"{arg}: not found")
        return

    print(f"{arg} is {executable_path}")


def handle_pwd():
    """Handle the pwd builtin command."""
    print(os.getcwd())


def handle_cd(arg):
    """Handle the cd builtin command."""
    if arg == "~":
        arg = str(Path.home())
        os.chdir(arg)
        return

    if not os.path.isdir(arg):
        sys.stderr.write(f"cd: {arg}: No such file or directory\n")
        return

    os.chdir(arg)


def handle_history(args=None):
    """Handle the history builtin command."""
    if not args:
        cmds = list(command_history)
        start = 1
    elif args[0] == '-r':
        if len(args) < 2:
            print("history: -r: filename argument required", file=sys.stderr)
            return

        load_history_from_file(args[1])
        return
    elif args[0] == '-a':
        if len(args) < 2:
            print("history: -a: filename argument required", file=sys.stderr)
            return

        append_history_to_file(args[1])
        return
    elif args[0] == '-w':
        if len(args) < 2:
            print("history: -w: filename argument required", file=sys.stderr)
            return

        write_history_to_file(args[1])
        return
    else:
        try:
            limit = int(args[0])
            cmds = list(command_history)[-limit:]
            start = len(command_history) - len(cmds) + 1
        except ValueError:
            cmds = list(command_history)
            start = 1

    for i, cmd in enumerate(cmds, start=start):
        print(f"{i:5d}  {cmd}")


def run_builtin(cmd, args):
    """
    Execute a builtin command.

    Returns:
        True if command was 'exit', False otherwise
    """
    if cmd == Command.EXIT:
        return True
    elif cmd == Command.ECHO:
        handle_echo(args)
    elif cmd == Command.TYPE:
        if args:
            handle_type(args[0])
    elif cmd == Command.PWD:
        handle_pwd()
    elif cmd == Command.CD:
        if args:
            handle_cd(args[0])
    elif cmd == Command.HISTORY:
        handle_history(args)

    return False


def execute_builtin(segment):
    """
    Execute a single builtin command with redirects (runs in parent process).

    Args:
        segment: Pipeline segment with 'parts', 'stdout_redirs', 'stderr_redirs'

    Returns:
        True if should exit shell, False otherwise
    """

    # Parse segment and prepare redirects
    cmd, args, stdout_spec, stderr_spec = parse_segment(segment)

    # Redirect stdout/stderr
    original_stdout = redirect_stdout(stdout_spec)
    original_stderr = redirect_stderr(stderr_spec)

    # Run the builtin
    should_exit = run_builtin(cmd, args)

    # Restore stdout/stderr
    restore_stdout(original_stdout)
    restore_stderr(original_stderr)

    return should_exit
