import os
import sys
import shutil
from pathlib import Path
from ..types import Command, is_builtin
from ..parsing import parse_segment, expand_path

HISTFILE = os.path.expanduser('~/.pynix_history')

# Storage for environment variables before venv activation
_venv_oldvars = {}

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
    Command.ABOUT: {
        "description": "Display help information for builtins",
        "usage": "about [builtin_name]"
    },
    Command.ACTIVATE: {
        "description": "Activate a Python virtual environment",
        "usage": "activate [venv_path]"
    },
    Command.DEACTIVATE: {
        "description": "Deactivate the current virtual environment",
        "usage": "deactivate"
    },
    Command.TRUE: {
        "description": "Returns success (exit code 0)",
        "usage": "true"
    },
    Command.FALSE: {
        "description": "Returns failure (exit code 1)",
        "usage": "false"
    },
}


def handle_echo(args, stdout=None):
    """Handle the echo builtin command."""
    stdout = stdout or sys.stdout
    print(' '.join(args), file=stdout)


def handle_type(arg, stdout=None):
    """Handle the type builtin command.

    Returns:
        True if command found, False if not found
    """
    stdout = stdout or sys.stdout
    if is_builtin(arg):
        print(f"{arg} is a shell builtin", file=stdout)
        return True

    path = shutil.which(arg)
    if path is None:
        print(f"{arg}: not found", file=stdout)
        return False

    print(f"{arg} is {path}", file=stdout)
    return True


def handle_pwd(stdout=None):
    """Handle the pwd builtin command."""
    stdout = stdout or sys.stdout
    print(os.getcwd(), file=stdout)


def handle_cd(arg, stderr=None):
    """Handle the cd builtin command.

    Returns:
        True if successful, False if failed
    """
    arg = expand_path(arg)

    if not os.path.isdir(arg):
        stderr = stderr or sys.stderr
        stderr.write(f"cd: {arg}: No such file or directory\n")
        return False

    os.chdir(arg)
    return True


def handle_activate(args=None):
    """Handle the activate builtin command."""

    venv_path = os.path.abspath(expand_path(args[0]) if args else '.venv')
    bin_dir = os.path.join(
        venv_path, 'Scripts' if sys.platform == 'win32' else 'bin')

    if not os.path.isdir(bin_dir):
        print(f"activate: '{venv_path}' is not a valid virtual environment")
        return False

    # Deactivate current venv if active
    if 'VIRTUAL_ENV' in os.environ:
        handle_deactivate()

    # Save old PATH for deactivation
    global _venv_oldvars
    _venv_oldvars = {'PATH': os.environ['PATH']}

    # Activate: prepend bin to PATH and set VIRTUAL_ENV
    os.environ['PATH'] = bin_dir + os.pathsep + os.environ['PATH']
    os.environ['VIRTUAL_ENV'] = venv_path
    os.environ.pop('PYTHONHOME', None)

    return True


def handle_deactivate():
    """Handle the deactivate builtin command."""

    if 'VIRTUAL_ENV' not in os.environ:
        print("deactivate: no virtual environment is active")
        return False

    # Restore PATH
    global _venv_oldvars
    if _venv_oldvars:
        os.environ.update(_venv_oldvars)
        _venv_oldvars.clear()

    del os.environ['VIRTUAL_ENV']

    return True


def handle_about(args=None, stdout=None):
    """Handle the about builtin command."""
    stdout = stdout or sys.stdout

    if not args:
        # Display all available builtins
        print("Available builtins:", file=stdout)
        for cmd in sorted(Command._value2member_map_.keys()):
            doc = command_docs.get(Command(cmd), {})
            desc = doc.get("description")
            print(f"  {cmd:12s} - {desc}", file=stdout)
        print("\nUse 'about <builtin>' for more information on a specific builtin.", file=stdout)
        return True

    # Display help for specific builtin
    builtin_name = args[0]
    if not is_builtin(builtin_name):
        print(f"about: no help topics match '{builtin_name}'.", file=stdout)
        return False

    cmd = Command(builtin_name)
    doc = command_docs.get(cmd, {})

    print(f"{builtin_name}: {doc.get('description', 'No description available')}", file=stdout)
    print(f"Usage: {doc.get('usage', builtin_name)}", file=stdout)

    return True


def handle_history(args=None, stdout=None, histfile=None):
    """Handle the history builtin command."""
    stdout = stdout or sys.stdout
    histfile = histfile or HISTFILE

    try:
        with open(histfile, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        lines = []

    cmds = []
    current_cmd = []
    for line in lines:
        line = line.rstrip('\n')
        if line.startswith('#'):
            if current_cmd:
                cmds.append('\n'.join(current_cmd))
                current_cmd = []
        elif line.startswith('+'):
            current_cmd.append(line[1:])

    if current_cmd:
        cmds.append('\n'.join(current_cmd))

    if args:
        try:
            limit = int(args[0])
            cmds = cmds[-limit:]
        except ValueError:
            pass

    for i, cmd in enumerate(cmds, start=1):
        display = cmd.split('\n')[0] if '\n' in cmd else cmd
        print(f"{i:5d}  {display}", file=stdout)


def run_builtin(cmd, args, stdout=None, stderr=None):
    """
    Execute a builtin command.

    Args:
        cmd: Command name
        args: Command arguments
        stdout: Optional stdout stream (defaults to sys.stdout)
        stderr: Optional stderr stream (defaults to sys.stderr)

    Returns:
        (should_exit, returncode) tuple
    """
    if cmd == Command.EXIT:
        return (True, 0)
    elif cmd == Command.ECHO:
        handle_echo(args, stdout=stdout)
        return (False, 0)
    elif cmd == Command.TYPE:
        if args:
            success = handle_type(args[0], stdout=stdout)
            return (False, 0 if success else 1)
        return (False, 0)
    elif cmd == Command.PWD:
        handle_pwd(stdout=stdout)
        return (False, 0)
    elif cmd == Command.CD:
        if args:
            success = handle_cd(args[0], stderr=stderr)
            return (False, 0 if success else 1)
        return (False, 0)
    elif cmd == Command.HISTORY:
        handle_history(args, stdout=stdout)
        return (False, 0)
    elif cmd == Command.ABOUT:
        success = handle_about(args, stdout=stdout)
        return (False, 0 if success else 1)
    elif cmd == Command.ACTIVATE:
        success = handle_activate(args)
        return (False, 0 if success else 1)
    elif cmd == Command.DEACTIVATE:
        success = handle_deactivate()
        return (False, 0 if success else 1)
    elif cmd == Command.TRUE:
        return (False, 0)
    elif cmd == Command.FALSE:
        return (False, 1)

    return (False, 0)


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
        should_exit, returncode = run_builtin(
            cmd, args, stdout=stdout, stderr=stderr)
        if result_holder is not None:
            result_holder['returncode'] = returncode
        return (should_exit, returncode)
    except Exception as e:
        print(f"Builtin error: {e}", file=stderr or sys.stderr)
        if result_holder is not None:
            result_holder['returncode'] = 1
        return (False, 1)
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
