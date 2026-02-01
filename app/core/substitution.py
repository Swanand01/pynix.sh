from ..types import CommandResult
from .external import execute_shell
from .execution import execute_python


def find_matching_paren(text, start):
    """
    Find the index of the closing parenthesis matching the one at start.

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
    in_single_quote = False
    in_double_quote = False

    while i < len(text) and depth > 0:
        char = text[i]

        # Handle escape sequences (only in double quotes)
        if char == '\\' and in_double_quote and i + 1 < len(text):
            i += 2
            continue

        # Track quote state
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
        elif char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
        # Count parentheses only outside quotes
        elif not in_single_quote and not in_double_quote:
            if char == '(':
                depth += 1
            elif char == ')':
                depth -= 1

        i += 1

    return i - 1 if depth == 0 else -1


def find_expansions(code):
    """
    Find all top-level $(), !(), @() patterns in code (not inside quotes).

    Args:
        code: Code string to search

    Returns:
        List of (start, end, operator, content) tuples, sorted right-to-left
    """
    expansions = []
    i = 0
    in_single_quote = False
    in_double_quote = False

    while i < len(code):
        char = code[i]

        # Handle escape sequences (only in double quotes)
        if char == '\\' and in_double_quote and i + 1 < len(code):
            i += 2
            continue

        # Track quote state
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
        elif char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
        # Look for $( or !( or @( only outside quotes
        elif not in_single_quote and not in_double_quote:
            if i < len(code) - 1 and char in ('$', '!', '@') and code[i + 1] == '(':
                paren_start = i + 1
                paren_end = find_matching_paren(code, paren_start)

                if paren_end != -1:
                    content = code[paren_start + 1:paren_end]
                    expansions.append((i, paren_end + 1, char, content))
                    i = paren_end + 1
                    continue

        i += 1

    # Sort by start position descending (process from right to left)
    return sorted(expansions, key=lambda x: x[0], reverse=True)


def stringify(value):
    """Convert a value to string for shell interpolation."""
    if isinstance(value, str):
        return value
    if hasattr(value, '__iter__'):
        return ' '.join(str(x) for x in value)
    return str(value)


def expand(code, namespace, context='python', expansions=None):
    """
    Recursively expand all $(), !(), and @() patterns.

    Args:
        code: Code string with expansion patterns
        namespace: Python namespace dict for evaluation and storage
        context: 'python' if result will be Python code, 'shell' for shell command
        expansions: Pre-found expansions (optional, to avoid re-scanning)

    Returns:
        Expanded code with all patterns replaced
    """
    if expansions is None:
        expansions = find_expansions(code)

    if not expansions:
        return code

    # Process each expansion (right to left to preserve indices)
    for i, (start, end, operator, content) in enumerate(expansions):
        # Recursively expand the content first (handles nesting)
        expanded_content = expand(content, namespace,
                                  context='python' if operator == '@' else 'shell')

        if operator == '@':
            # Python expression - evaluate and stringify
            try:
                result = execute_python(
                    expanded_content, return_value=True, namespace=namespace)
                result = stringify(result)
            except Exception as e:
                raise ValueError(f"Error evaluating @({content}): {e}")

            # Direct substitution for shell context
            code = code[:start] + result + code[end:]

        elif operator in ('$', '!'):
            # Shell command - execute and capture result
            returncode, stdout, stderr = execute_shell(
                expanded_content, capture=True)

            if context == 'shell':
                # Direct substitution for shell context
                result = stdout.rstrip('\n')
                code = code[:start] + result + code[end:]
            else:
                # Python context - store in namespace
                if operator == '$':
                    result = stdout.rstrip('\n')
                else:  # operator == '!'
                    result = CommandResult(returncode, stdout, stderr)
                var_name = f'__pynix_sub_{i}'
                namespace[var_name] = result
                code = code[:start] + var_name + code[end:]

    return code
