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

    # Check if valid Python syntax
    if not is_valid_python_syntax(parseable):
        # Invalid syntax - check if starts with Python keyword
        first = get_first_name(parseable)
        is_python = first and keyword.iskeyword(first)
        return is_python, expansions

    # Valid Python - check if statement or expression
    if is_python_statement(parseable):
        return True, expansions

    # It's an expression - determine if Python or shell
    is_python = is_python_expression(parseable)
    return is_python, expansions


def is_valid_python_syntax(code):
    """Check if code compiles as valid Python."""
    try:
        compile(code, '<string>', 'exec')
        return True
    except SyntaxError:
        return False


def is_python_statement(code):
    """Check if code is a Python statement (not an expression)."""
    try:
        compile(code, '<string>', 'eval')
        return False  # It's an expression
    except SyntaxError:
        return True  # It's a statement


def is_python_expression(code):
    """Determine if a valid expression should be treated as Python."""
    if code.isidentifier():
        return is_python_identifier(code)

    # Complex expression - analyze AST
    return analyze_expression_ast(code)


def is_python_identifier(identifier):
    """Check if a single identifier should be treated as Python."""
    if identifier == '__pynix_xp__':
        return True
    return is_python_name(identifier)


def analyze_expression_ast(code):
    """Analyze expression AST to determine if it's Python or shell."""
    try:
        tree = ast.parse(code, mode='eval')
    except SyntaxError:
        return False

    if has_strong_python_features(tree):
        return True

    if has_literals(tree):
        return True

    if has_operators_with_python_names(tree):
        return True

    return False


def has_strong_python_features(tree):
    """Check for AST nodes that strongly indicate Python code."""
    python_nodes = (ast.Call, ast.Subscript, ast.Attribute,
                    ast.ListComp, ast.DictComp, ast.SetComp, ast.Lambda)

    return any(isinstance(node, python_nodes) for node in ast.walk(tree))


def has_literals(tree):
    """Check if AST contains literal values."""
    literal_nodes = (ast.Constant, ast.List, ast.Dict, ast.Set, ast.Tuple)
    return any(isinstance(node, literal_nodes) for node in ast.walk(tree))


def has_operators_with_python_names(tree):
    """Check if expression has operators and operands exist in Python namespace."""
    operator_nodes = (ast.BinOp, ast.UnaryOp, ast.Compare)
    has_operators = any(isinstance(node, operator_nodes)
                        for node in ast.walk(tree))

    if not has_operators:
        return False

    # Check if any name operands exist in namespace
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id != '__pynix_xp__':
            if is_python_name(node.id):
                return True

    return False
