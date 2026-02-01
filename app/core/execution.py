import ast
import re
import sys
import traceback
from ..types import CommandResult, is_builtin


# Persistent namespace for Python code execution
python_namespace = {
    '__name__': '__main__',
    '__builtins__': __builtins__,
    'CommandResult': CommandResult,
}


def get_namespace():
    """Get the shared Python namespace."""
    return python_namespace


def execute_python(code_line, return_value=False, namespace=None):
    """
    Execute Python code with persistent namespace.

    Args:
        code_line: Python code string to execute (already expanded)
        return_value: If True, return the result instead of printing it
        namespace: Namespace dict (defaults to python_namespace)

    Returns:
        The evaluated result if return_value=True, else None

    Raises:
        ValueError: If return_value=True and evaluation fails
    """
    if namespace is None:
        namespace = python_namespace
    try:
        # Try as expression first
        try:
            result = eval(code_line, namespace)
            if return_value:
                return result
            if result is not None:
                print(result)
        except SyntaxError:
            # Not an expression, execute as statement
            exec(code_line, namespace)
    except KeyboardInterrupt:
        if return_value:
            raise ValueError("Interrupted")
        print("\nKeyboardInterrupt", file=sys.stderr)
    except SyntaxError as e:
        if return_value:
            raise ValueError(f"SyntaxError: {e.msg}")
        if e.text and e.offset:
            print(f"  {e.text.rstrip()}", file=sys.stderr)
            print(f"  {' ' * (e.offset - 1)}^", file=sys.stderr)
        print(f"SyntaxError: {e.msg}", file=sys.stderr)
    except Exception as e:
        if return_value:
            raise ValueError(f"Error evaluating '{code_line}': {e}")
        traceback.print_exc()


def is_python_name(name):
    """Check if a name exists in the Python namespace or builtins."""
    if name in python_namespace and name not in ('__name__', '__builtins__'):
        return True
    builtins = python_namespace.get('__builtins__')
    if isinstance(builtins, dict):
        return name in builtins
    return hasattr(builtins, name)


def replace_expansions_with_placeholder(command):
    """Replace $(), !(), @() with placeholder for Python parsing."""
    from .substitution import find_expansions

    expansions = find_expansions(command)
    result = command
    for start, end, _, _ in expansions:
        result = result[:start] + '__pynix_xp__' + result[end:]
    return result, expansions


def get_first_name(command):
    """Extract the first Python identifier from a command."""
    match = re.match(r'[a-zA-Z_][a-zA-Z0-9_]*', command)
    return match.group() if match else None


def is_python_code(command):
    """
    Check if a command should be executed as Python code.

    If all names in the expression exist
    in the current Python context, it's Python. Otherwise, it's shell.

    Returns:
        (is_python, expansions) tuple
    """
    command = command.strip()
    parseable, expansions = replace_expansions_with_placeholder(command)

    try:
        # Must be valid Python syntax
        compile(parseable, '<string>', 'exec')
    except SyntaxError:
        # Invalid syntax - check if first token is a Python name
        first = get_first_name(parseable)
        if first and not is_builtin(first) and is_python_name(first):
            return True, expansions
        return False, expansions

    # Statement (not expression) - treat as Python
    try:
        compile(parseable, '<string>', 'eval')
    except SyntaxError:
        return True, expansions

    # Single identifier
    if parseable.isidentifier():
        if parseable == '__pynix_xp__':
            return True, expansions
        if is_builtin(parseable):
            return False, expansions
        return is_python_name(parseable), expansions

    # Expression - check if all names exist in Python context
    try:
        tree = ast.parse(parseable, mode='eval')
    except SyntaxError:
        return False, expansions

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            if node.id == '__pynix_xp__':
                continue
            if not is_python_name(node.id):
                return False, expansions

    return True, expansions
