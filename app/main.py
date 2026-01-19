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


def main():
    while True:
        sys.stdout.write("$ ")
        command = input().strip()
        parts = command.split()

        if not parts:
            continue

        cmd = parts[0]
        args = parts[1:]

        if command == Command.EXIT:
            break
        elif cmd == Command.ECHO:
            handle_echo_command(command.replace("echo ", "", 1))
        elif cmd == Command.TYPE:
            if not args:
                continue
            handle_type_command(args[0])
        elif cmd == Command.PWD:
            handle_pwd_command()
        elif cmd == Command.CD:
            handle_cd_command(args[0])
        else:
            handle_external_command(cmd, args)


def handle_echo_command(args):
    try:
        tokens = shlex.split(args)
        print(' '.join(tokens))
    except ValueError:
        print(args)


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


def handle_external_command(cmd, args):
    file_exists, _ = file_exists_in_path(cmd)
    if not file_exists:
        print(f"{cmd}: command not found")
        return

    subprocess.run([cmd, *args])


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
