import shlex


def check_and_or(command, i):
    """Check if current position is a two-character operator (&& or ||)."""
    if i < len(command) - 1:
        two_char = command[i:i+2]
        if two_char in ('&&', '||'):
            return two_char
    return None


def update_quote_state(char, in_single_quote, in_double_quote):
    """Update quote tracking state based on current character."""
    if char == "'" and not in_double_quote:
        return not in_single_quote, in_double_quote
    if char == '"' and not in_single_quote:
        return in_single_quote, not in_double_quote
    return in_single_quote, in_double_quote


def tokenize_command(command):
    """Tokenize command string, falling back to simple split on error."""
    try:
        return shlex.split(command)
    except ValueError:
        return command.split()


def split_by_pipes(tokens):
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


def add_segment(segments, current_op, command, start, end):
    """Add a segment to the segments list if non-empty."""
    segment = command[start:end].strip()
    if segment:
        segments.append((current_op, segment))


def split_command_by_and_or(command):
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
            two_char_op = check_and_or(command, i)
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
