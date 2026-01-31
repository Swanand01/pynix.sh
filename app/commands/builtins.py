import os
import sys
from pathlib import Path
from ..types import Command, is_builtin
from ..utils import executable_exists_in_path
from ..parsing.redirection import parse_segment, expand_path
from ..history import command_history, load_history_from_file, append_history_to_file, write_history_to_file


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


def handle_echo(args, stdout=None):
    """Handle the echo builtin command."""
    stdout = stdout or sys.stdout
    print(' '.join(args), file=stdout)


def handle_type(arg, stdout=None):
    """Handle the type builtin command."""
    stdout = stdout or sys.stdout
    if is_builtin(arg):
        print(f"{arg} is a shell builtin", file=stdout)
        return

    executable_exists, executable_path = executable_exists_in_path(arg)
    if not executable_exists:
        print(f"{arg}: not found", file=stdout)
        return

    print(f"{arg} is {executable_path}", file=stdout)


def handle_pwd(stdout=None):
    """Handle the pwd builtin command."""
    stdout = stdout or sys.stdout
    print(os.getcwd(), file=stdout)


def handle_cd(arg):
    """Handle the cd builtin command."""
    arg = expand_path(arg)

    if not os.path.isdir(arg):
        sys.stderr.write(f"cd: {arg}: No such file or directory\n")
        return

    os.chdir(arg)


def handle_history(args=None, stdout=None, stderr=None):
    """Handle the history builtin command."""
    stdout = stdout or sys.stdout
    stderr = stderr or sys.stderr

    if not args:
        cmds = list(command_history)
        start = 1
    elif args[0] == '-r':
        if len(args) < 2:
            print("history: -r: filename argument required", file=stderr)
            return

        load_history_from_file(expand_path(args[1]))
        return
    elif args[0] == '-a':
        if len(args) < 2:
            print("history: -a: filename argument required", file=stderr)
            return

        append_history_to_file(expand_path(args[1]))
        return
    elif args[0] == '-w':
        if len(args) < 2:
            print("history: -w: filename argument required", file=stderr)
            return

        write_history_to_file(expand_path(args[1]))
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
        print(f"{i:5d}  {cmd}", file=stdout)


def run_builtin(cmd, args, stdout=None, stderr=None):
    """
    Execute a builtin command.

    Args:
        cmd: Command name
        args: Command arguments
        stdout: Optional stdout stream (defaults to sys.stdout)
        stderr: Optional stderr stream (defaults to sys.stderr)

    Returns:
        True if command was 'exit', False otherwise
    """
    if cmd == Command.EXIT:
        return True
    elif cmd == Command.ECHO:
        handle_echo(args, stdout=stdout)
    elif cmd == Command.TYPE:
        if args:
            handle_type(args[0], stdout=stdout)
    elif cmd == Command.PWD:
        handle_pwd(stdout=stdout)
    elif cmd == Command.CD:
        if args:
            handle_cd(args[0])
    elif cmd == Command.HISTORY:
        handle_history(args, stdout=stdout, stderr=stderr)

    return False


def execute_builtin(segment=None, cmd=None, args=None,
                    stdout=None, stderr=None,
                    close_stdout=False, result_holder=None):
    """
    Execute a builtin command.

    Can be called two ways:
    1. With segment (standalone): parses segment and opens redirect files
    2. With cmd/args/stdout/stderr (pipeline): uses provided file objects

    Args:
        segment: Pipeline segment with 'parts', 'stdout_redirs', 'stderr_redirs'
        cmd: Command name (used when segment is None)
        args: Command arguments (used when segment is None)
        stdout: Stdout file object (used when segment is None)
        stderr: Stderr file object (used when segment is None)
        close_stdout: If True, flush and close stdout after execution (for pipeline EOF)
        result_holder: Dict to store returncode (for threaded execution)

    Returns:
        True if should exit shell, False otherwise
    """
    owns_files = False

    if segment:
        # Standalone mode: parse segment and open redirect files
        cmd, args, stdout_spec, stderr_spec = parse_segment(segment)
        stdout = open(stdout_spec[0], stdout_spec[1]) if stdout_spec else None
        stderr = open(stderr_spec[0], stderr_spec[1]) if stderr_spec else None
        owns_files = True

    try:
        should_exit = run_builtin(cmd, args, stdout=stdout, stderr=stderr)
        if result_holder is not None:
            result_holder['returncode'] = 0
        return should_exit
    except Exception as e:
        print(f"Builtin error: {e}", file=stderr or sys.stderr)
        if result_holder is not None:
            result_holder['returncode'] = 1
        return False
    finally:
        if close_stdout and stdout and stdout not in (sys.stdout, sys.stderr):
            try:
                stdout.flush()
                stdout.close()
            except:
                pass
        elif owns_files:
            if stdout:
                stdout.close()
            if stderr:
                stderr.close()
