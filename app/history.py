from collections import deque
import sys

command_history = deque(maxlen=1000)
last_appended_index = 0


def add_to_history(command):
    """Add a command to the history."""
    command_history.append(command)


def load_history_from_file(filepath):
    """Load history from a file into memory."""
    try:
        with open(filepath, 'r') as f:
            for line in f:
                line = line.rstrip('\n')
                if line:
                    command_history.append(line)
    except FileNotFoundError:
        print(f"History file {filepath} not found.", file=sys.stderr)
    except Exception as e:
        print(f"Error loading history from {filepath}: {e}", file=sys.stderr)


def append_history_to_file(filepath):
    """Append new commands to file since last append."""
    global last_appended_index
    try:
        cmds = list(command_history)
        new_cmds = cmds[last_appended_index:]

        if new_cmds:
            with open(filepath, 'a') as f:
                for cmd in new_cmds:
                    f.write(cmd + '\n')
            last_appended_index = len(cmds)
    except Exception as e:
        print(f"history: {filepath}: {e}", file=sys.stderr)


def write_history_to_file(filepath):
    """Write all history to file."""
    try:
        with open(filepath, 'w') as f:
            for cmd in command_history:
                f.write(cmd + '\n')
    except Exception as e:
        print(f"history: {filepath}: {e}", file=sys.stderr)
