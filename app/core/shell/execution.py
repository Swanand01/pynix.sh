import subprocess
import sys
from ...parsing import parse_pipeline_into_segments, parse_segment
from ...parsing.tokenizer import update_quote_state
from ...types import is_builtin
from ...commands import execute_builtin


def split_on_unquoted_newlines(command):
    """Split command on newlines that are outside quotes."""
    lines = []
    current = []
    in_single = in_double = False

    for char in command:
        in_single, in_double = update_quote_state(char, in_single, in_double)
        if char == '\n' and not in_single and not in_double:
            lines.append(''.join(current))
            current = []
        else:
            current.append(char)

    if current:
        lines.append(''.join(current))
    return lines


def execute_shell_captured(pipeline, command):
    """Execute shell command in capture mode, returning output."""
    from .pipeline import execute_pipeline_captured

    if len(pipeline) == 1:
        result = execute_external(pipeline[0], capture=True)
        if result is None:
            return 127, '', f"{command}: command not found\n"
        return result
    return execute_pipeline_captured(pipeline)


def execute_single_shell_command(segment):
    """Execute a single shell command (builtin or external)."""
    cmd = segment['parts'][0] if segment['parts'] else None

    # Check if builtin
    if is_builtin(cmd):
        return execute_builtin(segment)

    # Execute external command
    returncode = execute_external(segment)
    if returncode is None:
        print(f"{cmd}: command not found", file=sys.stderr)
        return (False, 127)

    return (False, returncode)


def execute_shell(command, capture=False):
    """
    Execute a shell command (pipeline, builtin, or external).

    Args:
        command: Shell command string
        capture: If True, capture and return (returncode, stdout, stderr)

    Returns:
        If capture=False: (should_exit, returncode) tuple
        If capture=True: (returncode, stdout, stderr) tuple
    """
    from .pipeline import execute_pipeline

    pipeline = parse_pipeline_into_segments(command)

    # Capture mode - return output
    if capture:
        return execute_shell_captured(pipeline, command)

    # Interactive mode - pipeline
    if len(pipeline) > 1:
        returncode = execute_pipeline(pipeline)
        return (False, returncode)

    # Interactive mode - single command
    return execute_single_shell_command(pipeline[0])


def execute_external_captured(cmd, args):
    """Execute external command in capture mode, returning output."""
    try:
        result = subprocess.run(
            [cmd] + args,
            capture_output=True,
            text=True,
            timeout=300
        )
        return (result.returncode, result.stdout, result.stderr)
    except FileNotFoundError:
        return None
    except KeyboardInterrupt:
        return (130, '', '')


def open_redirect_file_handles(stdout_spec, stderr_spec):
    """
    Open file handles for stdout/stderr redirect specs.

    Args:
        stdout_spec: Tuple like ('/path', 'w') or None
        stderr_spec: Tuple like ('/path', 'w') or None

    Returns:
        (stdout_handle, stderr_handle, error) tuple
        Handles are open file objects or None, error is exception or None
    """
    stdout_arg = None
    stderr_arg = None

    try:
        if stdout_spec:
            stdout_arg = open(stdout_spec[0], stdout_spec[1])
        if stderr_spec:
            stderr_arg = open(stderr_spec[0], stderr_spec[1])
        return (stdout_arg, stderr_arg, None)
    except (FileNotFoundError, PermissionError, OSError) as e:
        # Clean up any opened handles on error
        if stdout_arg:
            stdout_arg.close()
        if stderr_arg:
            stderr_arg.close()
        return (None, None, e)


def run_subprocess_with_redirects(cmd, args, stdout_arg, stderr_arg):
    """Run subprocess with redirect file handles."""
    try:
        result = subprocess.run(
            [cmd] + args,
            stdout=stdout_arg,
            stderr=stderr_arg
        )
        return result.returncode
    except FileNotFoundError:
        return None
    except PermissionError:
        print(f"{cmd}: Permission denied", file=sys.stderr)
        return 126
    except OSError as e:
        print(f"{cmd}: {e}", file=sys.stderr)
        return 126
    except KeyboardInterrupt:
        return 130


def execute_external(segment, capture=False):
    """
    Execute a single external command with redirects (no fork needed).

    Args:
        segment: Pipeline segment with 'parts', 'stdout_redirs', 'stderr_redirs'
        capture: If True, capture and return (returncode, stdout, stderr) as strings

    Returns:
        If capture=False: returncode (int) or None if command not found
        If capture=True: (returncode, stdout, stderr) tuple or None if not found
    """

    # Parse segment and prepare redirects
    cmd, args, stdout_spec, stderr_spec = parse_segment(segment)

    # Capture mode - ignore redirects and use PIPE
    if capture:
        return execute_external_captured(cmd, args)

    # Open file handles for redirects
    stdout_arg, stderr_arg, error = open_redirect_file_handles(
        stdout_spec, stderr_spec)
    if error:
        print(f"Redirect error: {error}", file=sys.stderr)
        return 1

    # Run the command with redirects
    try:
        return run_subprocess_with_redirects(cmd, args, stdout_arg, stderr_arg)
    finally:
        # Always close file handles
        if stdout_arg:
            stdout_arg.close()
        if stderr_arg:
            stderr_arg.close()
