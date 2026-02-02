import sys
from .execution import execute_python, is_python_code, get_namespace
from .external import execute_shell
from .substitution import expand


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
    # Detect if this is Python code (also finds expansions)
    is_python, expansions = is_python_code(command)
    context = 'python' if is_python else 'shell'
    namespace = get_namespace()

    # Expand all operators ($, !, @)
    try:
        command = expand(command, namespace,
                         context=context, expansions=expansions)
    except ValueError as e:
        print(f"Expansion error: {e}", file=sys.stderr)
        return False

    # Execute based on detected type
    if is_python:
        execute_python(command)
    else:
        result = execute_shell(command)

    # Clean up substitution variables
    for key in [k for k in namespace if k.startswith('__pynix_sub_')]:
        del namespace[key]

    return result if not is_python else False
