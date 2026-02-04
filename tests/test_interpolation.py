"""Tests for Python expansions (@(), $(), !()) in shell commands and Python code."""

from app.core import run_command
from app.core.python.namespace import python_namespace
import unittest
import sys
import os
import tempfile
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestExpansionsInShell(unittest.TestCase):
    """Test Python expansions (@(), $(), !()) in shell commands."""

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

    def test_at_expansion_in_shell(self):
        """Test @() expansion in shell command."""
        run_command('x = 42; echo @(x)')

    def test_at_expansion_list_in_shell(self):
        """Test @() with list expansion in shell."""
        run_command('items = [1, 2, 3]; echo @(items)')

    def test_at_expansion_expression_in_shell(self):
        """Test @() with expression in shell."""
        run_command('x = 10; echo @(x * 2)')

    def test_dollar_expansion_in_shell(self):
        """Test $() command substitution in shell."""
        run_command('echo $(echo nested)')

    def test_nested_expansions_in_shell(self):
        """Test nested @() inside $()."""
        run_command('x = 5; result = $(echo @(x)); print(result)')
        self.assertEqual(sys.stdout.getvalue().strip(), '5')

    def test_multiple_same_expansion(self):
        """Test same @() expansion appearing multiple times in one command."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'snail')
            run_command(f'name = "snail"; echo @(name) > {tmpdir}/@(name)')
            # Verify file was created with correct name
            self.assertTrue(os.path.exists(output_file))
            with open(output_file) as f:
                self.assertEqual(f.read().strip(), 'snail')


class TestExpansionsInPython(unittest.TestCase):
    """Test shell expansions in Python code."""

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

    def test_dollar_in_assignment(self):
        """Test $() in Python assignment."""
        run_command('result = $(echo hello); print(result)')
        self.assertEqual(sys.stdout.getvalue().strip(), 'hello')

    def test_bang_in_assignment(self):
        """Test !() in Python assignment."""
        run_command('result = !(echo test); print(result.stdout)')
        self.assertIn('test', sys.stdout.getvalue())

    def test_at_in_python_expression(self):
        """Test @() in Python expression."""
        run_command('x = 10; y = @(x * 2); print(y)')
        self.assertEqual(sys.stdout.getvalue().strip(), '20')

    def test_expansion_in_for_loop(self):
        """Test expansions inside for loop (original bug)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            run_command(
                f'cd {tmpdir}; files = ["a.txt", "b.txt"]; for f in files: $(touch @(f))')
            # Check files were created
            self.assertTrue(os.path.exists(os.path.join(tmpdir, 'a.txt')))
            self.assertTrue(os.path.exists(os.path.join(tmpdir, 'b.txt')))

    def test_expansion_in_conditional(self):
        """Test expansion in if statement."""
        # Use proper multiline if syntax or inline expression
        run_command('x = 5')
        run_command('if x > 3: print("yes")')
        self.assertEqual(sys.stdout.getvalue().strip(), 'yes')


if __name__ == '__main__':
    unittest.main()
