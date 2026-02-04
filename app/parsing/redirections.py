from .utils import expand_path


def is_redirect_operator(token):
    """Check if token is a redirect operator."""
    return token in ('>', '1>', '>>', '1>>', '2>', '2>>')


def get_redirect_mode(operator):
    """Get file mode ('a' for append, 'w' for write) from redirect operator."""
    return 'a' if operator.endswith('>>') else 'w'


def add_redirect(operator, filename, stdout_redirs, stderr_redirs):
    """Add redirect to appropriate list based on operator type."""
    mode = get_redirect_mode(operator)
    if operator.startswith('2'):
        stderr_redirs.append((filename, mode))
    else:
        stdout_redirs.append((filename, mode))


def parse_redirection(parts):
    """
    Parse redirection operators from command parts.

    Returns:
        cleaned_parts: Command and args without redirection operators
        stdout_redirs: list[(path, mode)] in appearance order
        stderr_redirs: list[(path, mode)] in appearance order

    The last redirect in each list is the active target; earlier ones
    should still be created/truncated/appended to match bash behavior.
    """
    stdout_redirs = []
    stderr_redirs = []
    cleaned = []
    i = 0

    while i < len(parts):
        tok = parts[i]

        if is_redirect_operator(tok):
            # If there's no filename after the operator, drop operator
            if i + 1 >= len(parts):
                break

            filename = parts[i + 1]
            add_redirect(tok, filename, stdout_redirs, stderr_redirs)
            i += 2
            continue

        cleaned.append(tok)
        i += 1

    return cleaned, stdout_redirs, stderr_redirs


def prime_earlier_redirects(redirs):
    """Create/truncate earlier redirect files for bash-like side effects."""
    if not redirs:
        return
    for path, mode in redirs[:-1]:
        with open(expand_path(path), mode):
            pass


def get_active_redirect_spec(redirs):
    """Get the active (last) redirect spec, or None if no redirects."""
    if not redirs:
        return None
    path, mode = redirs[-1]
    return (expand_path(path), mode)


def prepare_redirect_specs(stdout_redirs, stderr_redirs):
    """
    Prime redirect files and get active specs (does NOT open files).

    Args:
        stdout_redirs: List of stdout redirect tuples
        stderr_redirs: List of stderr redirect tuples

    Returns:
        (stdout_spec, stderr_spec) - Active redirect specs or None
        Each spec is a tuple like ('/path/to/file', 'w') or None
    """
    # Prime earlier redirect files (create/truncate side effects)
    prime_earlier_redirects(stdout_redirs)
    prime_earlier_redirects(stderr_redirs)

    # Get active (last) redirect specs
    stdout_spec = get_active_redirect_spec(stdout_redirs)
    stderr_spec = get_active_redirect_spec(stderr_redirs)

    return stdout_spec, stderr_spec
