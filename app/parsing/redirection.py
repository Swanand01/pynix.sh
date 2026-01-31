import os


def expand_path(path):
    """Expand ~ in path."""
    return os.path.expanduser(path)


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
        with open(expand_path(path), mode):
            pass


def get_redirect_spec(redirs):
    """
    Get the active redirect specification (last one).

    Args:
        redirs: List of (path, mode) tuples

    Returns:
        Last redirect tuple (with expanded path) or None
    """
    if not redirs:
        return None
    path, mode = redirs[-1]
    return (expand_path(path), mode)


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
    args = [expand_path(arg) for arg in parts[1:]] if len(parts) > 1 else []

    stdout_spec, stderr_spec = prepare_redirects(
        segment['stdout_redirs'],
        segment['stderr_redirs']
    )

    return cmd, args, stdout_spec, stderr_spec
