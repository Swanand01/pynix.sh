import os
import shlex


def update_quote_state(char, in_single_quote, in_double_quote):
    """Update quote tracking state based on current character."""
    if char == "'" and not in_double_quote:
        return not in_single_quote, in_double_quote
    if char == '"' and not in_single_quote:
        return in_single_quote, not in_double_quote
    return in_single_quote, in_double_quote


def check_two_char_operator(command, i):
    """Check if current position is a two-character operator (&& or ||)."""
    if i < len(command) - 1:
        two_char = command[i:i+2]
        if two_char in ('&&', '||'):
            return two_char
    return None


def add_segment(segments, current_op, command, start, end):
    """Add a segment to the segments list if non-empty."""
    segment = command[start:end].strip()
    if segment:
        segments.append((current_op, segment))


def parse_control_flow(command):
    """
    Split command by &&, ||, ; operators (respecting quotes).

    Args:
        command: Raw command string

    Returns:
        List of (operator, segment) tuples where operator is the operator
        that comes BEFORE the segment (None for first segment):
        [(None, "cmd1"), ("&&", "cmd2"), ("||", "cmd3")]

    Example:
        "ls && pwd || echo fail" →
        [(None, "ls"), ("&&", "pwd"), ("||", "echo fail")]
    """
    segments = []
    current_start = 0
    current_op = None
    in_single_quote = False
    in_double_quote = False
    i = 0

    while i < len(command):
        char = command[i]

        # Handle escape sequences (only in double quotes)
        if char == '\\' and in_double_quote and i + 1 < len(command):
            i += 2
            continue

        # Update quote state
        in_single_quote, in_double_quote = update_quote_state(
            char, in_single_quote, in_double_quote
        )

        # Look for operators outside quotes
        if not in_single_quote and not in_double_quote:
            # Check for && or ||
            two_char_op = check_two_char_operator(command, i)
            if two_char_op:
                add_segment(segments, current_op, command, current_start, i)
                current_op = two_char_op
                current_start = i + 2
                i += 2
                continue

            # Check for ;
            if char == ';':
                add_segment(segments, current_op, command, current_start, i)
                current_op = ';'
                current_start = i + 1

        i += 1

    # Add final segment
    add_segment(segments, current_op, command, current_start, len(command))

    return segments if segments else [(None, command)]


def expand_path(path):
    """Expand ~ in path."""
    return os.path.expanduser(path)


def tokenize_command(command):
    """Tokenize command string, falling back to simple split on error."""
    try:
        return shlex.split(command)
    except ValueError:
        return command.split()


def split_on_pipes(tokens):
    """Split tokens on pipe operators into separate command segments."""
    segments = []
    current = []

    for token in tokens:
        if token == '|':
            if current:
                segments.append(current)
            current = []
        else:
            current.append(token)

    if current:
        segments.append(current)

    return segments


def build_pipeline_segments(token_segments):
    """Build pipeline segment dicts with redirections parsed."""
    pipeline = []
    for parts in token_segments:
        parts, stdout_redirs, stderr_redirs = parse_redirection(parts)
        pipeline.append({
            'parts': parts,
            'stdout_redirs': stdout_redirs,
            'stderr_redirs': stderr_redirs
        })
    return pipeline


def parse_pipeline(command):
    """
    Parse a pipeline command into segments.

    Args:
        command: Raw command string (e.g., "ls -l | grep py > out.txt")

    Returns:
        List of dicts with structure:
        [
            {'parts': ['ls', '-l'], 'stdout_redirs': [], 'stderr_redirs': []},
            {'parts': ['grep', 'py'], 'stdout_redirs': [('out.txt', 'w')], 'stderr_redirs': []}
        ]
    """
    tokens = tokenize_command(command)
    token_segments = split_on_pipes(tokens)
    return build_pipeline_segments(token_segments)


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


def prepare_redirects(stdout_redirs, stderr_redirs):
    """
    Prime redirect files and get active specs.

    Args:
        stdout_redirs: List of stdout redirect tuples
        stderr_redirs: List of stderr redirect tuples

    Returns:
        (stdout_spec, stderr_spec) - Active redirect specs or None
    """
    # Prime earlier redirect files (create/truncate side effects)
    prime_earlier_redirects(stdout_redirs)
    prime_earlier_redirects(stderr_redirs)

    # Get active (last) redirect specs
    stdout_spec = get_active_redirect_spec(stdout_redirs)
    stderr_spec = get_active_redirect_spec(stderr_redirs)

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
