from ..types import CommandResult
from ..parsing import parse_pipeline
from ..parsing.pipeline import execute_pipeline_captured
from .external import execute_external


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

        # Handle escape sequences in quotes
        if i > 0 and text[i - 1] == '\\':
            i += 1
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


def find_substitutions(code):
    """
    Find all $() and !() substitutions in code.

    Args:
        code: Python code string

    Returns:
        List of (start, end, operator, command) tuples, sorted innermost-first
    """
    substitutions = []
    i = 0

    while i < len(code):
        # Look for $( or !(
        if i < len(code) - 1 and code[i] in ('$', '!') and code[i + 1] == '(':
            operator = code[i]
            paren_start = i + 1
            paren_end = find_matching_paren(code, paren_start)

            if paren_end != -1:
                command = code[paren_start + 1:paren_end]
                substitutions.append((i, paren_end + 1, operator, command))
                i = paren_end + 1
                continue

        i += 1

    # Sort by start position descending (process from right to left)
    # This ensures replacements don't shift indices of earlier substitutions
    return sorted(substitutions, key=lambda x: x[0], reverse=True)


def execute_substitution(operator, command):
    """
    Execute a shell command and return the result.

    Args:
        operator: '$' for string output, '!' for CommandResult
        command: Shell command string to execute

    Returns:
        For $: stdout string (stripped)
        For !: CommandResult object
    """
    # Parse the command
    pipeline = parse_pipeline(command)

    # Execute and capture output
    if len(pipeline) == 1:
        # Single command
        result = execute_external(pipeline[0], capture=True)
        if result is None:
            returncode, stdout, stderr = 127, '', f"{command}: command not found\n"
        else:
            returncode, stdout, stderr = result
    else:
        # Pipeline
        returncode, stdout, stderr = execute_pipeline_captured(pipeline)

    # Return based on operator type
    if operator == '$':
        return stdout.rstrip('\n')
    else:
        return CommandResult(returncode, stdout, stderr)


def process_substitutions(code, namespace):
    """
    Process all $() and !() substitutions in code.

    Executes shell commands and replaces substitutions with placeholder
    variables that hold the results.

    Args:
        code: Python code string with substitutions
        namespace: Python namespace dict to store results

    Returns:
        Processed code with substitutions replaced by variable references
    """
    substitutions = find_substitutions(code)

    if not substitutions:
        return code

    # Process each substitution (right to left to preserve indices)
    for i, (start, end, operator, command) in enumerate(substitutions):
        # Execute the command
        result = execute_substitution(operator, command)

        # Store result in namespace with a unique variable name
        var_name = f'_subst_{i}'
        namespace[var_name] = result

        # Replace substitution with variable reference
        code = code[:start] + var_name + code[end:]

    return code
