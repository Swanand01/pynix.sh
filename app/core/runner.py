import sys
from .execution import execute_python, is_python_code, get_namespace
from .external import execute_shell
from .substitution import expand
from ..parsing import parse_control_flow


def run_command(command):
    """Execute a single command line."""
    segments = parse_control_flow(command)
    namespace = get_namespace()
    cleanup_keys = set()
    last_returncode = 0

    for operator, cmd_segment in segments:
        should_exit = execute_segment(
            operator,
            cmd_segment,
            namespace,
            last_returncode,
            cleanup_keys
        )

        if should_exit is True:
            return True

        if should_exit is not None:
            last_returncode = should_exit

    cleanup_substitutions(namespace, cleanup_keys)
    return False


def should_skip_segment(operator, last_returncode):
    """Check if segment should be skipped based on operator and previous return code."""
    if operator == "&&" and last_returncode != 0:
        return True
    if operator == "||" and last_returncode == 0:
        return True
    return False


def expand_segment(cmd_segment, namespace, context, expansions, cleanup_keys):
    """Expand substitutions in a command segment."""
    try:
        expanded = expand(cmd_segment, namespace,
                          context=context, expansions=expansions)
        cleanup_keys.update(
            k for k in namespace if k.startswith('__pynix_sub_'))
        return expanded
    except ValueError as e:
        print(f"Expansion error: {e}", file=sys.stderr)
        return None


def execute_python_segment(expanded):
    """Execute a Python code segment and return the exit code."""
    # Handle boolean literals specially
    if expanded.strip() in ('True', 'False'):
        print(expanded.strip())
        return 0 if expanded.strip() == 'True' else 1

    success = execute_python(expanded)
    return 0 if success else 1


def execute_shell_segment(expanded):
    """Execute a shell command segment. Returns True if should exit, or returncode."""
    should_exit, returncode = execute_shell(expanded)
    return True if should_exit else returncode


def execute_segment(operator, cmd_segment, namespace, last_returncode, cleanup_keys):
    """
    Execute a single command segment.

    Returns:
        - True: shell should exit
        - int: return code to update last_returncode
        - None: segment was skipped
    """
    # Short-circuit evaluation
    if should_skip_segment(operator, last_returncode):
        return None

    # Detect if Python code and find expansions
    is_python, expansions = is_python_code(cmd_segment)
    context = 'python' if is_python else 'shell'

    # Expand substitutions
    expanded = expand_segment(cmd_segment, namespace,
                              context, expansions, cleanup_keys)
    if expanded is None:
        return 1

    # Execute based on type
    if is_python:
        return execute_python_segment(expanded)
    else:
        return execute_shell_segment(expanded)


def cleanup_substitutions(namespace, cleanup_keys):
    """Remove temporary substitution variables from namespace."""
    for key in cleanup_keys:
        if key in namespace:
            del namespace[key]
