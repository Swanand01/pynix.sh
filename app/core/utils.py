"""
Utility functions for expansion and scope management.
"""

import sys


def get_caller_scope(depth=2):
    """
    Get the combined scope (globals + locals) from the caller's frame.

    Args:
        depth: Stack depth to inspect (2 = caller's caller, which accounts for this helper)

    Returns:
        Dictionary with merged globals and locals (locals override globals)
    """
    caller_frame = sys._getframe(depth)
    return {**caller_frame.f_globals, **caller_frame.f_locals}
