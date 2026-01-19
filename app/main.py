import sys
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
        command = input()

        if command == Command.EXIT:
            break
        elif command.split()[0] == Command.ECHO:
            args = command.split()[1:]
            print(" ".join(args))
        elif command.split()[0] == Command.TYPE:
            arg = command.split()[1]
            if arg in list(Command):
                print(f"{arg} is a shell builtin")
            else:
                print(f"{arg}: not found")
        else:
            print(f"{command}: command not found")


if __name__ == "__main__":
    main()
