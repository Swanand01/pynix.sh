import sys
from .execution import execute_python, is_python_code, get_namespace
from .external import execute_shell
from .substitution import expand
from ..parsing import parse_control_flow


def run_command(command):
    """
    Detect, expand, and execute a command.

    Args:
        command: Raw command string from user input

    Returns:
        True if shell should exit, False otherwise
    """
    # Handle multiline input by running each line separately
    if '\n' in command:
        for line in command.split('\n'):
            line = line.strip()
            if line:
                if run_single_command(line):
                    return True
        return False

    return run_single_command(command)


def run_single_command(command):
    """Execute a single command line."""
    # Parse control flow FIRST (before expansion)
    segments = parse_control_flow(command)
    namespace = get_namespace()

    # Execute segments sequentially with short-circuit logic
    last_returncode = 0

    for operator, cmd_segment in segments:
        # Short-circuit evaluation
        if operator == "&&" and last_returncode != 0:
            continue  # Skip: previous command failed
        if operator == "||" and last_returncode == 0:
            continue  # Skip: previous command succeeded
        # operator == ";" or None → always execute

        # Detect if this segment is Python code (also finds expansions)
        is_python, expansions = is_python_code(cmd_segment)
        context = 'python' if is_python else 'shell'

        # Expand all operators ($, !, @) for THIS segment
        try:
            expanded = expand(cmd_segment, namespace,
                              context=context, expansions=expansions)
        except ValueError as e:
            print(f"Expansion error: {e}", file=sys.stderr)
            last_returncode = 1
            continue

        # Execute based on detected type
        if is_python:
            execute_python(expanded)
            last_returncode = 0  # Python code doesn't fail
        else:
            should_exit, returncode = execute_shell(expanded)
            last_returncode = returncode
            if should_exit:
                # Clean up substitution variables before exiting
                for key in [k for k in namespace if k.startswith('__pynix_sub_')]:
                    del namespace[key]
                return True

    # Clean up substitution variables
    for key in [k for k in namespace if k.startswith('__pynix_sub_')]:
        del namespace[key]

    return False
