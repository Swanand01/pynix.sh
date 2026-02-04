import sys
import traceback
from .namespace import python_namespace


def execute_python(code_line, namespace=None, interactive=True):
    """
    Execute Python code with persistent namespace.

    Args:
        code_line: Python code string to execute (already transformed by AST)
        namespace: Namespace dict (defaults to python_namespace)
        interactive: If True, print errors to stderr and return success bool.
                    If False, raise errors and return the evaluation result.

    Returns:
        If interactive=True: bool (True on success, False on error)
        If interactive=False: any (the evaluated result, or None for statements)

    Raises:
        ValueError: If interactive=False and an error occurs
    """
    if namespace is None:
        namespace = python_namespace

    try:
        # Try as expression first
        try:
            result = eval(code_line, namespace)

            if not interactive:
                return result

            if result is not None:
                print(result)
            return True
        except SyntaxError:
            # Not an expression, execute as statement
            exec(code_line, namespace)
            return True if interactive else None

    except KeyboardInterrupt:
        if not interactive:
            raise ValueError("Interrupted")

        print("\nKeyboardInterrupt", file=sys.stderr)
        return False

    except SyntaxError as e:
        if not interactive:
            raise ValueError(f"SyntaxError: {e.msg}")

        if e.text and e.offset:
            print(f"  {e.text.rstrip()}", file=sys.stderr)
            print(f"  {' ' * (e.offset - 1)}^", file=sys.stderr)
        print(f"SyntaxError: {e.msg}", file=sys.stderr)
        return False

    except Exception as e:
        if not interactive:
            raise ValueError(f"Error evaluating '{code_line}': {e}")

        traceback.print_exc()
        return False
