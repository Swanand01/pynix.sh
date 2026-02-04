import ast


def find_expansions(code):
    """
    Find all top-level $(), !(), @() expansions in code.
    Returns list of (operator, content, start, end).
    """
    expansions = []
    i = 0

    while i < len(code):
        if i < len(code) - 1:
            two_char = code[i:i+2]
            if two_char in ('$(', '!(', '@('):
                close_paren = find_matching_paren(code, i + 1)

                if close_paren != -1:
                    operator = two_char[0]
                    content = code[i+2:close_paren]
                    expansions.append((operator, content, i, close_paren + 1))
                    i = close_paren + 1
                    continue
        i += 1

    return expansions


def find_matching_paren(text, start):
    """
    Find the index of the matching closing parenthesis.

    Args:
        text: String to search in
        start: Index of the opening parenthesis

    Returns:
        Index of matching closing paren, or -1 if not found
    """
    if start >= len(text) or text[start] != '(':
        return -1

    depth = 1
    i = start + 1

    while i < len(text) and depth > 0:
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
        i += 1

    return i - 1 if depth == 0 else -1


def replace_expansions_with_placeholders(code):
    """
    Replace $(), !(), @() with __PH_N__ placeholders so Python can parse it.
    Returns (modified_code, mapping).
    """
    expansions = find_expansions(code)
    mapping = {}

    # Replace from end to start to preserve positions
    modified = code
    for idx, (op, content, start, end) in enumerate(reversed(expansions)):
        placeholder = f'__PH_{len(expansions) - idx - 1}__'
        mapping[placeholder] = (op, content)
        modified = modified[:start] + placeholder + modified[end:]

    return modified, mapping


def parse_expansion_content(content, operator):
    """
    Recursively parse expansion content into AST.

    For @(expr): Parse as Python expression (must be valid Python)
    For $(cmd) or !(cmd): Keep as string, expand @() recursively at runtime
    """
    if operator == '@':
        # @(expr) - parse as Python expression
        try:
            return ast.parse(content, mode='eval').body
        except SyntaxError:
            # If it's not valid Python, wrap as string
            return ast.Constant(value=content)
    else:
        return ast.Constant(value=content)
