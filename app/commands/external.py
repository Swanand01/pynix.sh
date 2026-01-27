import subprocess
import sys
from ..redirection import parse_segment


def execute_external(segment):
    """
    Execute a single external command with redirects (no fork needed).

    Args:
        segment: Pipeline segment with 'parts', 'stdout_redirs', 'stderr_redirs'
    """

    # Parse segment and prepare redirects
    cmd, args, stdout_spec, stderr_spec = parse_segment(segment)

    # Open file handles for redirects
    stdout_arg = open(stdout_spec[0], stdout_spec[1]) if stdout_spec else None
    stderr_arg = open(stderr_spec[0], stderr_spec[1]) if stderr_spec else None

    # Run the command
    try:
        subprocess.run([cmd] + args, stdout=stdout_arg, stderr=stderr_arg)
    except FileNotFoundError:
        print(f"{cmd}: command not found", file=sys.stderr)
    finally:
        # Close file handles
        if stdout_arg:
            stdout_arg.close()
        if stderr_arg:
            stderr_arg.close()
