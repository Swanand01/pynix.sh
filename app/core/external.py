import subprocess
import sys
from ..parsing import parse_pipeline, parse_segment
from .pipeline import execute_pipeline, execute_pipeline_captured
from ..types import is_builtin
from ..commands import execute_builtin


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
    pipeline = parse_pipeline(command)

    # Capture mode - return output
    if capture:
        if len(pipeline) == 1:
            result = execute_external(pipeline[0], capture=True)
            if result is None:
                return 127, '', f"{command}: command not found\n"
            return result
        else:
            return execute_pipeline_captured(pipeline)

    # Interactive mode - display output
    if len(pipeline) > 1:
        returncode = execute_pipeline(pipeline)
        return (False, returncode)

    segment = pipeline[0]
    cmd = segment['parts'][0] if segment['parts'] else None

    # Single command - check if builtin
    if is_builtin(cmd):
        return execute_builtin(segment)

    # Single command - external
    returncode = execute_external(segment)
    if returncode is None:
        print(f"{cmd}: command not found", file=sys.stderr)
        return (False, 127)

    return (False, returncode)


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

    # Parse segment and prepare redirects (includes ~ expansion)
    cmd, args, stdout_spec, stderr_spec = parse_segment(segment)

    # If capturing, ignore redirects and use PIPE
    if capture:
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

    # Open file handles for redirects
    stdout_arg = None
    stderr_arg = None

    # Open file handles for redirects
    try:
        if stdout_spec:
            stdout_arg = open(stdout_spec[0], stdout_spec[1])
        if stderr_spec:
            stderr_arg = open(stderr_spec[0], stderr_spec[1])
    except (FileNotFoundError, PermissionError, OSError) as e:
        print(f"Redirect error: {e}", file=sys.stderr)

        if stdout_arg:
            stdout_arg.close()
        if stderr_arg:
            stderr_arg.close()
        return 1

    # Run the command
    try:
        result = subprocess.run(
            [cmd] + args, stdout=stdout_arg, stderr=stderr_arg)
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
    finally:
        # Close file handles
        if stdout_arg:
            stdout_arg.close()
        if stderr_arg:
            stderr_arg.close()
