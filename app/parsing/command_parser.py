import os
import shlex


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
    i = 0
    in_single_quote = False
    in_double_quote = False

    while i < len(command):
        char = command[i]

        # Handle escape sequences (only in double quotes)
        if char == '\\' and in_double_quote and i + 1 < len(command):
            i += 2
            continue

        # Track quote state
        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
        elif char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
        # Look for operators outside quotes
        elif not in_single_quote and not in_double_quote:
            # Check for && or ||
            if i < len(command) - 1:
                two_char = command[i:i+2]
                if two_char in ('&&', '||'):
                    # Save previous segment
                    segment = command[current_start:i].strip()
                    if segment:
                        segments.append((current_op, segment))
                    current_op = two_char
                    current_start = i + 2
                    i += 2
                    continue
            # Check for ;
            if char == ';':
                segment = command[current_start:i].strip()
                if segment:
                    segments.append((current_op, segment))
                current_op = ';'
                current_start = i + 1

        i += 1

    # Final segment
    segment = command[current_start:].strip()
    if segment:
        segments.append((current_op, segment))

    return segments if segments else [(None, command)]


def expand_path(path):
    """Expand ~ in path."""
    return os.path.expanduser(path)


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
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()

    # Split on | tokens
    segments = []
    current = []
    for token in tokens:
        if token != '|':
            current.append(token)
            continue
        if current:
            segments.append(current)
        current = []
    if current:
        segments.append(current)

    pipeline = []
    for parts in segments:
        parts, stdout_redirs, stderr_redirs = parse_redirection(parts)
        pipeline.append({
            'parts': parts,
            'stdout_redirs': stdout_redirs,
            'stderr_redirs': stderr_redirs
        })

    return pipeline


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
        if tok in ('>', '1>', '>>', '1>>', '2>', '2>>'):
            # If there's no filename after the operator, drop operator
            if i + 1 >= len(parts):
                break

            filename = parts[i + 1]
            mode = 'a' if tok.endswith('>>') else 'w'
            if tok.startswith('2'):
                stderr_redirs.append((filename, mode))
            else:
                stdout_redirs.append((filename, mode))
            i += 2
            continue

        cleaned.append(tok)
        i += 1

    return cleaned, stdout_redirs, stderr_redirs


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
    for redirs in (stdout_redirs, stderr_redirs):
        if redirs:
            for path, mode in redirs[:-1]:
                with open(expand_path(path), mode):
                    pass

    # Get active (last) redirect spec
    def get_spec(redirs):
        if not redirs:
            return None
        path, mode = redirs[-1]
        return (expand_path(path), mode)

    return get_spec(stdout_redirs), get_spec(stderr_redirs)


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
