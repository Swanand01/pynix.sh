import os
import sys
import subprocess
from enum import Enum


class Command(str, Enum):
    EXIT = 'exit'
    ECHO = 'echo'
    TYPE = 'type'


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
    }
}


def main():
    while True:
        sys.stdout.write("$ ")
        command = input().strip()

        if command == Command.EXIT:
            break
        elif command.split()[0] == Command.ECHO:
            args = command.split()[1:]
            print(" ".join(args))
        elif command.split()[0] == Command.TYPE:
            arg = command.split()[1]
            if command_exists(arg):
                print(f"{arg} is a shell builtin")
            else:
                file_exists, file_path = file_exists_in_path(arg)
                if file_exists:
                    print(f"{arg} is {file_path}")
                else:
                    print(f"{arg}: not found")
        else:
            external_command = command.split()[0]
            file_exists, file_path = file_exists_in_path(external_command)
            if file_exists:
                subprocess.run([file_path, *command.split()[1:]])
            else:
                print(f"{external_command}: command not found")


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
