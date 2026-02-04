"""Tests for namespace-based shell/Python detection."""

from app.core import run_command
from app.core.python.namespace import python_namespace
import unittest
import sys
import os
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestNamespaceDetection(unittest.TestCase):
    """Test namespace-based shell/Python detection."""

    def setUp(self):
        """Clear namespace and capture output."""
        keys_to_remove = [k for k in python_namespace.keys()
                          if not k.startswith('_') and k not in ('__name__', '__builtins__', 'CommandResult')]
        for k in keys_to_remove:
            del python_namespace[k]
        self.held_stdout = sys.stdout
        self.held_stderr = sys.stderr
        sys.stdout = StringIO()
        sys.stderr = StringIO()

    def tearDown(self):
        """Restore stdout/stderr."""
        sys.stdout = self.held_stdout
        sys.stderr = self.held_stderr

    def test_undefined_is_shell(self):
        """Test undefined name is treated as shell."""
        run_command('pwd')

    def test_python_builtin_is_python(self):
        """Test Python builtin is detected."""
        run_command('print("test")')
        self.assertEqual(sys.stdout.getvalue().strip(), 'test')

    def test_variable_shadows_shell(self):
        """Test Python variable shadows shell command."""
        run_command('ls = 100; ls + 1')
        self.assertEqual(sys.stdout.getvalue().strip(), '101')

    def test_ls_with_args_is_shell(self):
        """Test ls with args detected as shell even if ls defined."""
        run_command('ls = 2; ls -la')


if __name__ == '__main__':
    unittest.main()
