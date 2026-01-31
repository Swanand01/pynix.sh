import ast
import os
import sys
import code
import shutil
import traceback
from keyword import iskeyword
from ..types import CommandResult
from .substitution import process_substitutions


# Persistent namespace for Python code execution
python_namespace = {
    '__name__': '__main__',
    '__builtins__': __builtins__,
    'CommandResult': CommandResult,
}


def execute_python(code_line):
    """
    Execute Python code with persistent namespace.

    Supports shell substitution operators:
    - $(cmd) - Replaced with stdout of cmd as a string
    - !(cmd) - Replaced with CommandResult object

    Args:
        code_line: Python code string to execute
    """
    try:
        # Process $() and !() substitutions
        code_line = process_substitutions(code_line, python_namespace)

        # Try as expression first
        try:
            result = eval(code_line, python_namespace)
            if result is not None:
                print(result)
        except SyntaxError:
            # Not an expression, execute as statement
            exec(code_line, python_namespace)
    except KeyboardInterrupt:
        # User pressed Ctrl+C during execution
        print("\nKeyboardInterrupt", file=sys.stderr)
    except SyntaxError as e:
        if e.text and e.offset:
            print(f"  {e.text.rstrip()}", file=sys.stderr)
            print(f"  {' ' * (e.offset - 1)}^", file=sys.stderr)
        print(f"SyntaxError: {e.msg}", file=sys.stderr)
    except Exception:
        traceback.print_exc()


def is_command_valid(cmd):
    """
    Check if a command exists in PATH.

    Args:
        cmd: Command name to check

    Returns:
        bool: True if command exists and is not a Python keyword
    """
    # Don't highlight Python keywords as shell commands
    if iskeyword(cmd):
        return False
    # Check if command exists in PATH
    return shutil.which(cmd) is not None


def is_python_code_complete(text):
    """
    Check if Python code is complete and ready to execute.

    Args:
        text: Python code string

    Returns:
        bool: True if code is complete, False if more input is needed
        None: If there's a syntax error
    """
    try:
        compiled = code.compile_command(text)
        # None means incomplete, needs more input
        # A code object means complete
        return compiled is not None
    except SyntaxError:
        # Syntax error means code is malformed but "complete"
        return True


def get_auto_indent(text):
    """
    Calculate auto-indent for Python code based on the last line.

    Args:
        text: Current text in the buffer

    Returns:
        str: String of spaces for indentation
    """
    lines = text.split('\n')
    if not lines:
        return ''

    # Find the last non-empty line
    for line in reversed(lines):
        if line.strip():
            indent = len(line) - len(line.lstrip())
            # If line ends with colon, increase indent
            if line.rstrip().endswith(':'):
                return ' ' * (indent + 4)
            # Otherwise maintain current indent
            return ' ' * indent
    return ''


def is_file_path(path_str):
    """
    Check if a string is a valid file path.

    Args:
        path_str: String to check

    Returns:
        bool: True if it's a valid existing path
    """
    try:
        path = os.path.expanduser(path_str)
        return os.path.exists(path)
    except (OSError, ValueError):
        return False


def is_python_name(name):
    """
    Check if a name exists in the Python namespace or builtins.

    Args:
        name: String to check

    Returns:
        bool: True if the name exists in the Python namespace or builtins
    """
    # Check direct namespace (user-defined variables)
    if name in python_namespace and name not in ('__name__', '__builtins__'):
        return True
    # Check builtins (print, len, range, etc.)
    builtins = python_namespace.get('__builtins__')
    if isinstance(builtins, dict):
        return name in builtins
    return hasattr(builtins, name)


def has_substitution(command):
    """Check if command contains $() or !() substitution operators."""
    i = 0
    while i < len(command) - 1:
        if command[i] in ('$', '!') and command[i + 1] == '(':
            return True
        i += 1
    return False


def is_python_code(command):
    """
    Check if a command should be executed as Python code.

    Returns True if:
    - It contains $() or !() substitution operators
    - It's a Python statement (assignment, def, import, etc.)
    - It's an expression referencing Python variables

    Args:
        command: Command string to check

    Returns:
        bool: True if should execute as Python
    """
    command = command.strip()

    # Commands with $() or !() are always Python
    if has_substitution(command):
        return True

    # Try to compile as statement (exec mode)
    # Statements like "ls = 2", "def foo():", etc. only compile in exec mode
    try:
        compile(command, '<string>', 'exec')
        # If it compiles in exec mode, check if it's NOT just a simple expression
        try:
            compile(command, '<string>', 'eval')
            # It's a valid expression
            # For simple identifiers, check if they're in namespace
            if command.isidentifier():
                return is_python_name(command)

            # For complex expressions, check if all names are defined
            # This prevents "ls -la" (valid Python: ls minus la) from being treated as Python
            try:
                tree = ast.parse(command, mode='eval')
                # Check if all names used in the expression exist in namespace
                for node in ast.walk(tree):
                    if isinstance(node, ast.Name):
                        if not is_python_name(node.id):
                            # Name not in namespace - probably a shell command
                            return False
                # All names are defined - it's Python code
                return True
            except:
                # If AST parsing fails for some reason, be conservative
                return False
        except SyntaxError:
            # Compiles as statement but not expression - it's Python code (assignment, etc.)
            return True
    except SyntaxError:
        # Doesn't compile as Python - it's a shell command
        return False
