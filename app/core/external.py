import subprocess
import sys
from ..parsing.redirection import parse_segment


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
        return True  # Command was found but not executable
    finally:
        # Close file handles
        if stdout_arg:
            stdout_arg.close()
        if stderr_arg:
            stderr_arg.close()
