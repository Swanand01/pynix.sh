"""Tests for pipes in shell, Python, and mixed contexts."""

from app.core import run_command
from app.core.python.namespace import python_namespace
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPipelines(unittest.TestCase):
    """Test pipes in shell, Python, and mixed contexts."""

    def setUp(self):
        """Clear namespace."""
        keys_to_remove = [k for k in python_namespace.keys()
                          if not k.startswith('_') and k not in ('__name__', '__builtins__', 'CommandResult')]
        for k in keys_to_remove:
            del python_namespace[k]

    def test_shell_pipe(self):
        """Test shell command pipeline."""
        run_command('echo hello | grep h')

    def test_shell_pipe_multiple(self):
        """Test multi-stage shell pipeline."""
        run_command('echo testing | grep test | grep ing')

    def test_python_with_captured_pipe(self):
        """Test Python capturing shell pipeline output."""
        run_command('result = $(echo hello | grep h); print(result)')


if __name__ == '__main__':
    unittest.main()
