"""
Shared utility functions for parsing.
"""

import os


def expand_path(path):
    """Expand ~ in path."""
    return os.path.expanduser(path)
