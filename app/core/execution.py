import ast
import keyword
import re
import sys
import traceback
from ..types import CommandResult


# Persistent namespace for Python code execution
python_namespace = {
    '__name__': '__main__',
    '__builtins__': __builtins__,
    'CommandResult': CommandResult,
}


def get_namespace():
    """Get the shared Python namespace."""
    return python_namespace


def execute_python(code_line, namespace=None, interactive=True):
    """
    Execute Python code with persistent namespace.

    Args:
        code_line: Python code string to execute (already expanded)
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

    Uses syntax-based heuristics rather than name checking.

    Returns:
        (is_python, expansions) tuple
    """
    command = command.strip()
    parseable, expansions = replace_expansions_with_placeholder(command)

    try:
        # Must be valid Python syntax
        compile(parseable, '<string>', 'exec')
    except SyntaxError:
        # Compilation failed
        first = get_first_name(parseable)

        # Python keyword? → Python (even with syntax error)
        if first and keyword.iskeyword(first):
            return True, expansions

        return False, expansions

    # Check if it's a statement (not an expression)
    try:
        compile(parseable, '<string>', 'eval')
    except SyntaxError:
        # It's a statement (def, class, for, if, assignment, etc.) → Python
        return True, expansions

    # It's a valid expression - check if it looks like Python
    if parseable.isidentifier():
        if parseable == '__pynix_xp__':
            return True, expansions
        # If it exists in Python namespace, treat as Python
        return is_python_name(parseable), expansions

    # Complex expression (operators, calls, subscripts, etc.)
    # Parse the AST to check if it has Python-like features
    try:
        tree = ast.parse(parseable, mode='eval')

        # Strong Python indicators (definitely not shell commands)
        has_strong_python_features = any(
            isinstance(node, (ast.Call, ast.Subscript, ast.Attribute,
                              ast.ListComp, ast.DictComp, ast.SetComp,
                              ast.Lambda))
            for node in ast.walk(tree)
        )

        if has_strong_python_features:
            return True, expansions

        # Has operators with literals (like "2 + 2", "'hello' + 'world'") → Python
        has_operators = any(
            isinstance(node, (ast.BinOp, ast.UnaryOp, ast.Compare))
            for node in ast.walk(tree)
        )

        has_literals = any(
            isinstance(node, (ast.Constant, ast.List,
                              ast.Dict, ast.Set, ast.Tuple))
            for node in ast.walk(tree)
        )

        # Pure literals (like "[1,2,3]", "{'a': 1}", "(1,2)") → Python
        if has_literals:
            return True, expansions

        # Has operators but no literals - check if operand names exist in Python namespace
        if has_operators:
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and node.id != '__pynix_xp__':
                    if is_python_name(node.id):
                        # At least one name exists → treat as Python
                        return True, expansions

        # No Python features found
        return False, expansions

    except SyntaxError:
        return False, expansions
