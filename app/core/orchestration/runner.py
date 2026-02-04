import sys
from ..python import execute_python, get_namespace
from ...parsing import split_command_by_and_or, transform_code_with_expansions


def run_command(command):
    """Execute a single command line."""
    segments = split_command_by_and_or(command)
    namespace = get_namespace()
    last_returncode = 0

    for operator, cmd_segment in segments:
        should_exit = execute_segment(
            operator,
            cmd_segment,
            namespace,
            last_returncode
        )

        if should_exit is True:
            return True

        if should_exit is not None:
            last_returncode = should_exit

    return False


def should_skip_segment(operator, last_returncode):
    """Check if segment should be skipped based on operator and previous return code."""
    if operator == "&&" and last_returncode != 0:
        return True
    if operator == "||" and last_returncode == 0:
        return True
    return False


def execute_segment(operator, cmd_segment, namespace, last_returncode):
    """
    Execute a single command segment - UNIFIED LANGUAGE APPROACH.

    Everything goes through AST transformation:
    - Python code with expansions → AST transform
    - Shell commands → wrapped in __shell() call

    Returns:
        - True: shell should exit
        - int: return code
        - None: segment was skipped
    """
    # Short-circuit evaluation
    if should_skip_segment(operator, last_returncode):
        return None

    # Transform everything through AST, passing namespace for shell detection
    try:
        transformed = transform_code_with_expansions(
            cmd_segment,
            namespace=namespace
        )
        execute_python(transformed, namespace=namespace)

        # Get the return code from namespace (__shell stores it as __last_returncode__)
        return namespace.get('__last_returncode__', 0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
