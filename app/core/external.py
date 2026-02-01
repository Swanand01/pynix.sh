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
        If capture=False: True if shell should exit, False otherwise
        If capture=True: (returncode, stdout, stderr) tuple
    """
    pipeline = parse_pipeline(command)

    if capture:
        # Capture mode - return output
        if len(pipeline) == 1:
            result = execute_external(pipeline[0], capture=True)
            if result is None:
                return 127, '', f"{command}: command not found\n"
            return result
        else:
            return execute_pipeline_captured(pipeline)

    # Interactive mode - display output
    if len(pipeline) > 1:
        execute_pipeline(pipeline)
        return False

    segment = pipeline[0]
    cmd = segment['parts'][0] if segment['parts'] else None

    if is_builtin(cmd):
        return execute_builtin(segment)

    if not execute_external(segment):
        print(f"{cmd}: command not found", file=sys.stderr)

    return False


def execute_external(segment, capture=False):
    """
    Execute a single external command with redirects (no fork needed).

    Args:
        segment: Pipeline segment with 'parts', 'stdout_redirs', 'stderr_redirs'
        capture: If True, capture and return (returncode, stdout, stderr) as strings

    Returns:
        If capture=False: True if command found, False if not found
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
                text=True
            )
            return (result.returncode, result.stdout, result.stderr)
        except FileNotFoundError:
            return None
        except KeyboardInterrupt:
            return (130, '', '')

    # Open file handles for redirects
    stdout_arg = open(stdout_spec[0], stdout_spec[1]) if stdout_spec else None
    stderr_arg = open(stderr_spec[0], stderr_spec[1]) if stderr_spec else None

    # Run the command
    try:
        subprocess.run([cmd] + args, stdout=stdout_arg, stderr=stderr_arg)
        return True
    except FileNotFoundError:
        return False
    except PermissionError:
        print(f"{cmd}: Permission denied", file=sys.stderr)
        return True
    except KeyboardInterrupt:
        return True
    finally:
        # Close file handles
        if stdout_arg:
            stdout_arg.close()
        if stderr_arg:
            stderr_arg.close()
