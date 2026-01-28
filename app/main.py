import os
from pathlib import Path
from .command_parser import parse_pipeline
from .commands import (
    is_builtin,
    execute_builtin,
    execute_external,
    setup_completion,
    add_to_history,
    load_history_from_file,
    write_history_to_file
)
from .pipeline import execute_pipeline


def main():
    """Main REPL loop for the shell."""
    setup_completion()

    histfile = os.environ.get('HISTFILE')
    if histfile:
        load_history_from_file(histfile)

    home = str(Path.home())

    while True:
        cwd = os.getcwd()
        prompt_dir = cwd.replace(home, "~") if cwd.startswith(home) else cwd
        command = input(f"$ ").strip()

        if not command:
            continue

        # Add to history
        add_to_history(command)

        # Parse command into pipeline segments
        pipeline = parse_pipeline(command)

        # Handle pipelines
        if len(pipeline) > 1:
            execute_pipeline(pipeline)
            continue

        # Single command
        segment = pipeline[0]
        cmd = segment['parts'][0] if segment['parts'] else None

        # Handle external
        if not is_builtin(cmd):
            execute_external(segment)
            continue

        # Handle builtin
        should_exit = execute_builtin(segment)
        if should_exit:
            if histfile:
                write_history_to_file(histfile)
            break


if __name__ == "__main__":
    main()
