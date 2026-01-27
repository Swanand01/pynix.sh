import sys

from .command_parser import parse_pipeline
from .commands import (
    is_builtin,
    execute_builtin,
    execute_external,
    setup_completion
)
from .pipeline import execute_pipeline


def main():
    """Main REPL loop for the shell."""
    setup_completion()

    while True:
        command = input("$ ").strip()

        if not command:
            continue

        # Parse command into pipeline segments
        pipeline = parse_pipeline(command)

        # Handle pipelines
        if len(pipeline) > 1:
            execute_pipeline(pipeline)
            continue

        # Single command
        segment = pipeline[0]
        cmd = segment['parts'][0] if segment['parts'] else None

        # Handle builtin
        if is_builtin(cmd):
            if execute_builtin(segment):
                break  # Exit if builtin returned True
            continue

        # Handle external
        execute_external(segment)


if __name__ == "__main__":
    main()
