import sys


def redirect_stdout(stdout_spec):
    """
    Redirect stdout to a file.

    Args:
        stdout_spec: None or tuple(path, mode) where mode is 'w' or 'a'

    Returns:
        Original stdout or None
    """
    if stdout_spec:
        stdout_file, mode = stdout_spec
        original = sys.stdout
        sys.stdout = open(stdout_file, mode)
        return original
    return None


def restore_stdout(original):
    """Restore original stdout."""
    if original:
        sys.stdout.close()
        sys.stdout = original


def redirect_stderr(stderr_spec):
    """
    Redirect stderr to a file.

    Args:
        stderr_spec: None or tuple(path, mode) where mode is 'w' or 'a'

    Returns:
        Original stderr or None
    """
    if stderr_spec:
        stderr_file, mode = stderr_spec
        original = sys.stderr
        sys.stderr = open(stderr_file, mode)
        return original
    return None


def restore_stderr(original):
    """Restore original stderr."""
    if original:
        sys.stderr.close()
        sys.stderr = original


def prime_redirect_files(redirs):
    """
    Create/truncate/append earlier redirect files (all but last).

    This matches bash behavior where all redirect files are opened
    in order, but only the last one receives output.
    """
    if not redirs:
        return
    for path, mode in redirs[:-1]:
        # Open and close to apply side-effect (create/truncate or create for append)
        with open(path, mode):
            pass


def get_redirect_spec(redirs):
    """
    Get the active redirect specification (last one).

    Args:
        redirs: List of (path, mode) tuples

    Returns:
        Last redirect tuple or None
    """
    return redirs[-1] if redirs else None


def prepare_redirects(stdout_redirs, stderr_redirs):
    """
    Prime redirect files and get active specs.

    Args:
        stdout_redirs: List of stdout redirect tuples
        stderr_redirs: List of stderr redirect tuples

    Returns:
        (stdout_spec, stderr_spec) - Active redirect specs or None
    """
    prime_redirect_files(stdout_redirs)
    prime_redirect_files(stderr_redirs)

    stdout_spec = get_redirect_spec(stdout_redirs)
    stderr_spec = get_redirect_spec(stderr_redirs)

    return stdout_spec, stderr_spec


def parse_segment(segment):
    """
    Extract command info and prepare redirects from a pipeline segment.

    Args:
        segment: Dict with 'parts', 'stdout_redirs', 'stderr_redirs'

    Returns:
        (cmd, args, stdout_spec, stderr_spec)
    """
    parts = segment['parts']
    cmd = parts[0] if parts else None
    args = parts[1:] if len(parts) > 1 else []

    stdout_spec, stderr_spec = prepare_redirects(
        segment['stdout_redirs'],
        segment['stderr_redirs']
    )

    return cmd, args, stdout_spec, stderr_spec
