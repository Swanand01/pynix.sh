"""Tests for mixed Python and shell execution with operators (&&, ||, ;)."""

from app.core import run_command
from app.core.python.namespace import python_namespace
import unittest
import sys
import os
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMixedExecution(unittest.TestCase):
    """Test mixed Python and shell execution with operators."""

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

    def test_python_then_shell_with_semicolon(self):
        """Test Python followed by shell with ;."""
        run_command('x = 5; echo hello')

    def test_shell_then_python_with_semicolon(self):
        """Test shell followed by Python with ;."""
        run_command('echo test; print(2 + 2)')
        self.assertIn('4', sys.stdout.getvalue())

    def test_shell_and_operator(self):
        """Test shell && operator."""
        run_command('true && echo success')
        self.assertIn('success', sys.stdout.getvalue())

    def test_shell_and_operator_failure(self):
        """Test && stops on failure."""
        run_command('false && echo should_not_run')

    def test_shell_or_operator(self):
        """Test shell || operator."""
        run_command('false || echo fallback')

    def test_python_and_shell_mixed_with_and(self):
        """Test Python and shell mixed with &&."""
        run_command('x = 5; true && print(x)')
        self.assertIn('5', sys.stdout.getvalue())

    def test_expansion_with_and_operator(self):
        """Test expansion with && operator (original bug scenario)."""
        run_command('x = 2; true && echo @(x) && false && echo @(x * 2)')


if __name__ == '__main__':
    unittest.main()
