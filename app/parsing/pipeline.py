"""
Pipeline parsing for shell commands with pipe operators.
"""

from .tokenizer import tokenize_command, split_by_pipes
from .redirections import parse_redirection


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


def parse_pipeline_into_segments(command):
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
    token_segments = split_by_pipes(tokens)
    return build_pipeline_segments(token_segments)
