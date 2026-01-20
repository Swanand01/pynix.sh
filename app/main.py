import sys
import shlex

from .command_parser import parse_redirection
from .redirection import (
    redirect_stdout,
    restore_stdout,
    redirect_stderr,
    restore_stderr,
    prime_redirect_files,
)
from .commands import (
    Command,
    command_exists,
    handle_builtin_command,
    handle_external_command,
    setup_completion
)


def main():
    """Main REPL loop for the shell."""
    setup_completion(list(Command))

    while True:
        sys.stdout.write("$ ")
        command = input().strip()

        try:
            parts = shlex.split(command)
        except ValueError:
            parts = command.split()

        if not parts:
            continue

        parts, stdout_redirs, stderr_redirs = parse_redirection(parts)
        cmd = parts[0] if parts else None
        args = parts[1:] if len(parts) > 1 else []

        original_stdout = None
        original_stderr = None

        # Prime earlier redirect files (create/truncate them)
        prime_redirect_files(stdout_redirs)
        prime_redirect_files(stderr_redirs)

        # Get the last redirect for each stream (the active one)
        stdout_spec = stdout_redirs[-1] if stdout_redirs else None
        stderr_spec = stderr_redirs[-1] if stderr_redirs else None

        # Redirect for builtin commands
        if cmd in [Command.ECHO, Command.PWD, Command.TYPE, Command.CD]:
            original_stdout = redirect_stdout(stdout_spec)
            original_stderr = redirect_stderr(stderr_spec)

        # Execute command
        if command_exists(cmd):
            should_exit = handle_builtin_command(cmd, args)
            if should_exit:
                break
        else:
            handle_external_command(cmd, args, stdout_spec, stderr_spec)

        # Restore original stdout/stderr
        restore_stdout(original_stdout)
        restore_stderr(original_stderr)


if __name__ == "__main__":
    main()
