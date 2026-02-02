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
    return run_single_command(command)


def run_single_command(command):
    """Execute a single command line."""
    # Parse control flow FIRST (before expansion)
    segments = parse_control_flow(command)
    namespace = get_namespace()

    # Execute segments sequentially with short-circuit logic
    last_returncode = 0
    cleanup_keys = set()  # Track temp variables to clean up

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
            # Track any new substitution variables created
            cleanup_keys.update(
                k for k in namespace if k.startswith('__pynix_sub_'))
        except ValueError as e:
            print(f"Expansion error: {e}", file=sys.stderr)
            last_returncode = 1
            continue

        # Execute based on detected type
        if is_python:
            # If expanded to boolean literal, treat as exit code
            if expanded.strip() in ('True', 'False'):
                print(expanded.strip())
                last_returncode = 0 if expanded.strip() == 'True' else 1
            else:
                success = execute_python(expanded)
                last_returncode = 0 if success else 1
        else:
            should_exit, returncode = execute_shell(expanded)
            last_returncode = returncode
            if should_exit:
                return True

    # Clean up all substitution variables collected during execution
    for key in cleanup_keys:
        if key in namespace:
            del namespace[key]

    return False
