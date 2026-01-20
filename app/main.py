import os
import sys
import subprocess
import shlex
from enum import Enum
from pathlib import Path


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


def redirect_stdout(stdout_file):
    if stdout_file:
        original = sys.stdout
        sys.stdout = open(stdout_file, 'w')
        return original
    return None


def restore_stdout(original):
    if original:
        sys.stdout.close()
        sys.stdout = original


def redirect_stderr(stderr_file):
    if stderr_file:
        original = sys.stderr
        sys.stderr = open(stderr_file, 'w')
        return original
    return None


def restore_stderr(original):
    if original:
        sys.stderr.close()
        sys.stderr = original


def main():
    while True:
        sys.stdout.write("$ ")
        command = input().strip()

        try:
            parts = shlex.split(command)
        except ValueError:
            parts = command.split()

        if not parts:
            continue

        parts, stdout_file, stderr_file = parse_redirection(parts)
        cmd = parts[0] if parts else None
        args = parts[1:] if len(parts) > 1 else []

        original_stdout = None
        original_stderr = None
        if cmd in [Command.ECHO, Command.PWD, Command.TYPE]:
            original_stdout = redirect_stdout(stdout_file)
            original_stderr = redirect_stderr(stderr_file)

        if command == Command.EXIT:
            break
        elif cmd == Command.ECHO:
            handle_echo_command(args)
        elif cmd == Command.TYPE:
            if not args:
                continue
            handle_type_command(args[0])
        elif cmd == Command.PWD:
            handle_pwd_command()
        elif cmd == Command.CD:
            if not args:
                continue
            handle_cd_command(args[0])
        else:
            handle_external_command(cmd, args, stdout_file, stderr_file)

        # Restore output for built-in commands
        restore_stdout(original_stdout)
        restore_stderr(original_stderr)


def parse_redirection(parts):
    # Normalize 1> to >
    parts = ['>' if p == '1>' else p for p in parts]

    stdout_file = None
    stderr_file = None

    # Check for stdout redirection
    if '>' in parts:
        idx = parts.index('>')
        stdout_file = parts[idx + 1] if idx + 1 < len(parts) else None
        parts = parts[:idx] + parts[idx + 2:]  # Remove > and filename

    # Check for stderr redirection
    if '2>' in parts:
        idx = parts.index('2>')
        stderr_file = parts[idx + 1] if idx + 1 < len(parts) else None
        parts = parts[:idx] + parts[idx + 2:]  # Remove 2> and filename

    return parts, stdout_file, stderr_file


def handle_echo_command(args):
    print(' '.join(args))


def handle_type_command(arg):
    if command_exists(arg):
        print(f"{arg} is a shell builtin")
        return

    file_exists, file_path = file_exists_in_path(arg)
    if not file_exists:
        print(f"{arg}: not found")
        return

    print(f"{arg} is {file_path}")


def handle_pwd_command():
    print(os.getcwd())


def handle_cd_command(arg):
    if arg == "~":
        arg = str(Path.home())
        os.chdir(arg)
        return

    if not os.path.isdir(arg):
        print(f"cd: {arg}: No such file or directory")
        return

    os.chdir(arg)


def handle_external_command(cmd, args, stdout_file=None, stderr_file=None):
    file_exists, _ = file_exists_in_path(cmd)
    if not file_exists:
        print(f"{cmd}: command not found")
        return

    stdout_arg = open(stdout_file, 'w') if stdout_file else None
    stderr_arg = open(stderr_file, 'w') if stderr_file else None

    subprocess.run([cmd, *args], stdout=stdout_arg, stderr=stderr_arg)

    if stdout_arg:
        stdout_arg.close()
    if stderr_arg:
        stderr_arg.close()


def command_exists(command):
    return command in list(Command)


def file_exists_in_path(filename):
    path = os.environ['PATH']
    directories = path.split(os.pathsep)
    for directory in directories:
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path) and os.access(file_path, os.X_OK):
            return True, file_path
    return False, None


if __name__ == "__main__":
    main()
