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
