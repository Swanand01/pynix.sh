"""Shared types and enums used across modules."""

from enum import Enum


class Command(str, Enum):
    """Shell builtin commands."""
    EXIT = 'exit'
    ECHO = 'echo'
    TYPE = 'type'
    PWD = 'pwd'
    CD = 'cd'
    HISTORY = 'history'


def is_builtin(command):
    """Check if a command is a shell builtin."""
    return command in list(Command)


class CommandResult:
    """
    Result of a shell command execution via !() operator.

    Attributes:
        stdout: Standard output as string
        stderr: Standard error as string
        returncode: Exit code of the command
    """

    def __init__(self, returncode, stdout, stderr):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    def __repr__(self):
        return f"CommandResult(returncode={self.returncode})"

    def __str__(self):
        return self.stdout

    def __bool__(self):
        return self.returncode == 0
