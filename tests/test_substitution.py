"""Tests for shell command execution."""

from app.core import run_command
from app.core.python.namespace import python_namespace
import unittest
import sys
import os
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestShellExecution(unittest.TestCase):
    """Test pure shell command execution."""

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

    def test_shell_echo(self):
        """Test shell echo command."""
        # Use $() to capture output
        run_command('result = $(echo test); print(result)')
        self.assertEqual(sys.stdout.getvalue().strip(), 'test')

    def test_shell_with_args(self):
        """Test shell command with arguments."""
        run_command('result = $(echo hello world); print(result)')
        self.assertEqual(sys.stdout.getvalue().strip(), 'hello world')

    def test_shell_ls(self):
        """Test shell ls command."""
        # Just verify it runs without error - output varies by directory
        run_command('result = !(ls); print("returncode:", result.returncode)')
        self.assertIn('returncode: 0', sys.stdout.getvalue())

    def test_shell_pwd(self):
        """Test shell pwd command."""
        # Ensure we're in a valid directory (test isolation issue)
        project_root = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))
        os.chdir(project_root)
        # pwd returns the current directory - just verify it executes
        run_command('result = !(pwd)')
        self.assertIn('result', python_namespace)
        self.assertEqual(python_namespace['result'].returncode, 0)


if __name__ == '__main__':
    unittest.main()
