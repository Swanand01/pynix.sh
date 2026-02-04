from .redirections import prepare_redirect_specs
from .utils import expand_path


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

    stdout_spec, stderr_spec = prepare_redirect_specs(
        segment['stdout_redirs'],
        segment['stderr_redirs']
    )

    return cmd, args, stdout_spec, stderr_spec
