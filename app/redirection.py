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
