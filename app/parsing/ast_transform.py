import ast
import builtins as builtin_module
import keyword
from .expansions import replace_expansions_with_placeholders, parse_expansion_content


class ExpansionTransformer(ast.NodeTransformer):
    """Transform placeholders in AST to runtime function calls with recursive parsing."""

    def __init__(self, mapping):
        self.mapping = mapping  # placeholder -> (operator, content)

    def visit_Name(self, node):
        """Replace __PH_N__ names with proper expansion calls."""
        if node.id in self.mapping:
            operator, content = self.mapping[node.id]

            # Recursively parse the content
            content_ast = parse_expansion_content(content, operator)

            # Map operators to appropriate function calls
            if operator == '@':
                # @() uses __expand_at (formats already-evaluated value)
                return ast.Call(
                    func=ast.Name(id='__expand_at', ctx=ast.Load()),
                    args=[content_ast],
                    keywords=[],
                    lineno=node.lineno,
                    col_offset=node.col_offset
                )
            elif operator == '$':
                # $() uses __shell with capture='stdout'
                return ast.Call(
                    func=ast.Name(id='__shell', ctx=ast.Load()),
                    args=[content_ast],
                    keywords=[ast.keyword(
                        arg='capture', value=ast.Constant(value='stdout'))],
                    lineno=node.lineno,
                    col_offset=node.col_offset
                )
            elif operator == '!':
                # !() uses __shell with capture='full'
                return ast.Call(
                    func=ast.Name(id='__shell', ctx=ast.Load()),
                    args=[content_ast],
                    keywords=[ast.keyword(
                        arg='capture', value=ast.Constant(value='full'))],
                    lineno=node.lineno,
                    col_offset=node.col_offset
                )

        return node


def transform_code_with_expansions(code, mode='exec', namespace=None):
    """
    Transform code with $(), !(), @() into executable Python with runtime calls.

    Args:
        code: Source code to transform
        mode: Parse mode ('exec', 'eval', 'single')
        namespace: Dict of available variables for shell detection
    """
    code = code.strip()

    # Step 1: Try to parse as Python
    modified_code, mapping = replace_expansions_with_placeholders(code)

    try:
        tree = ast.parse(modified_code, mode=mode)

        if is_likely_shell_command(tree, namespace):
            return f'__shell({repr(code)})'

        # Valid Python - transform expansions
        transformer = ExpansionTransformer(mapping)
        transformed_tree = transformer.visit(tree)
        ast.fix_missing_locations(transformed_tree)
        return ast.unparse(transformed_tree)

    except SyntaxError:
        if looks_like_python_syntax(code):
            raise
        return f'__shell({repr(code)})'


def looks_like_python_syntax(code):
    """
    Check if code looks like it was intended to be Python.
    Used to distinguish Python syntax errors from shell commands.
    """
    # Get first word
    words = code.split()
    if not words:
        return False

    first_word = words[0]

    # Python keywords indicate Python code (includes def, class, import, from, etc.)
    if keyword.iskeyword(first_word):
        return True

    # Assignment operator indicates Python
    if '=' in code and not code.startswith('='):
        return True

    # Unmatched brackets/parens suggest incomplete Python
    open_brackets = code.count('(') + code.count('[') + code.count('{')
    close_brackets = code.count(')') + code.count(']') + code.count('}')
    if open_brackets != close_brackets:
        return True

    return False


def is_likely_shell_command(tree, namespace=None):
    """
    Heuristic: detect if parsed Python is actually a shell command.

    Args:
        tree: Parsed AST
        namespace: Dict with current variables (globals merged with locals)
    """
    if namespace is None:
        namespace = {}

    # Only check single expression statements
    if len(tree.body) != 1 or not isinstance(tree.body[0], ast.Expr):
        return False

    expr = tree.body[0].value

    # Don't treat comprehensions as shell commands
    if isinstance(expr, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
        return False

    # Collect all names used in the expression
    names = {node.id for node in ast.walk(expr) if isinstance(node, ast.Name)}

    if not names:
        return False

    # Check if ANY name doesn't exist in namespace

    for name in names:
        # Skip special names and placeholders
        if name.startswith('__'):
            continue

        # Check namespace (includes both globals and locals)
        if name in namespace:
            continue

        # Check Python builtins
        if hasattr(builtin_module, name):
            continue

        # This name doesn't exist - likely shell command
        return True

    return False
