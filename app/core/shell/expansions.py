import re
from ..utils import get_caller_scope


def has_redirections(cmd):
    """
    Check if command has output redirections (>, >>, 2>, etc.).

    Returns:
        True if command has redirections that would be ignored in capture mode
    """
    # Simple check for common redirection operators
    # Don't need perfect parsing - just detect if we should avoid capture mode
    return bool(re.search(r'\s+>>?\s+|\s+2>>?\s+|\s+&>>?\s+', cmd))


def expand_at(value):
    """
    Runtime @() operator - converts Python value to string.

    Args:
        value: Any Python value (already evaluated by Python's normal scoping)

    Returns:
        String representation of the value, with lists/tuples joined by spaces
    """
    # Handle lists and tuples specially - join with spaces for shell
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            return ''
        return ' '.join(str(item) for item in value)

    return str(value)


def expand_nested_substitutions(text, scope):
    """
    Expand @(), $(), !() patterns in text recursively.

    Args:
        text: String that may contain @(), $(), !() patterns
        scope: Dictionary of variables for eval()

    Returns:
        String with all patterns expanded
    """
    from ...parsing import find_matching_paren
    from ..python.execution import execute_python
    from .execution import execute_shell

    result = text
    offset = 0
    i = 0

    while i < len(result):
        if i < len(result) - 1:
            two_char = result[i:i+2]
            if two_char in ('@(', '$(', '!('):
                close_paren = find_matching_paren(result, i + 1)

                if close_paren != -1:
                    operator = two_char[0]
                    content = result[i+2:close_paren]

                    try:
                        if operator == '@':
                            # Recursively expand nested patterns first
                            expanded_content = expand_nested_substitutions(
                                content, scope)
                            # Python expression
                            value = execute_python(
                                expanded_content, namespace=scope, interactive=False)
                            replacement = expand_at(value)
                        else:  # $ or !
                            expanded_cmd = expand_nested_substitutions(
                                content, scope)
                            _, stdout, _ = execute_shell(
                                expanded_cmd, capture=True)
                            replacement = stdout.strip() if stdout else ''
                    except Exception as e:
                        error_msg = str(e)
                        if "Error evaluating" in error_msg:
                            # Strip the wrapper from execute_python
                            error_msg = error_msg.split(": ", 1)[-1]

                        raise RuntimeError(
                            f"{operator}({content}): {error_msg}") from None

                    # Replace
                    start = i + offset
                    end = close_paren + 1 + offset
                    result = result[:start] + replacement + result[end:]
                    offset += len(replacement) - (close_paren + 1 - i)

                    i = close_paren + 1
                    continue
        i += 1

    return result


def shell(cmd_template, capture=None):
    """
    Unified shell execution - handles all shell command execution modes.

    Args:
        cmd_template: Shell command string, may contain @(), $(), !() placeholders
        capture: None → side effects only (returns None)
                'stdout' → returns stdout string (for $())
                'full' → returns CommandResult (for !())

    Returns:
        None, str, or CommandResult depending on capture mode
    """
    import sys
    from .execution import execute_shell
    from ...types import CommandResult

    # Get caller's scope for expanding patterns
    scope = get_caller_scope()

    # Expand all patterns recursively
    cmd = expand_nested_substitutions(cmd_template, scope)

    # Handle redirections (can't capture when output goes to file)
    if has_redirections(cmd):
        should_exit, returncode = execute_shell(cmd, capture=False)

        if capture is None:
            # Store returncode in caller's namespace for $? and && ||
            caller_frame = sys._getframe(1)
            caller_frame.f_globals['__last_returncode__'] = returncode
            if should_exit:
                sys.exit(returncode)
            return None
        elif capture == 'stdout':
            return ""
        elif capture == 'full':
            return CommandResult(returncode, "", "")

    # Normal execution (no redirections)
    if capture is None:
        # Standalone command - display output, store returncode
        should_exit, returncode = execute_shell(cmd, capture=False)
        caller_frame = sys._getframe(1)
        caller_frame.f_globals['__last_returncode__'] = returncode
        if should_exit:
            sys.exit(returncode)
        return None

    elif capture == 'stdout':
        # $() mode - capture and return stdout
        returncode, stdout, stderr = execute_shell(cmd, capture=True)
        return stdout.strip() if stdout else ""

    elif capture == 'full':
        # !() mode - capture and return full result
        returncode, stdout, stderr = execute_shell(cmd, capture=True)
        return CommandResult(returncode, stdout if stdout else "", stderr if stderr else "")
