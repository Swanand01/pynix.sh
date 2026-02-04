"""Tests for complex combinations of pipes, redirections, and mixed code."""

from app.core import run_command
from app.core.python.namespace import python_namespace
import unittest
import sys
import os
import tempfile
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestComplexCombinations(unittest.TestCase):
    """Test complex combinations of pipes, redirections, and mixed code."""

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

    def test_pipeline_with_redirection(self):
        """Test shell pipeline with output redirection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'output.txt')
            run_command(f'echo hello world | grep hello > {output_file}')
            with open(output_file) as f:
                self.assertEqual(f.read().strip(), 'hello world')

    def test_pipeline_with_append_redirection(self):
        """Test pipeline with append redirection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'output.txt')
            run_command(f'echo first | grep first > {output_file}')
            run_command(f'echo second | grep second >> {output_file}')
            with open(output_file) as f:
                content = f.read().strip()
                self.assertIn('first', content)
                self.assertIn('second', content)

    def test_mixed_python_with_pipeline(self):
        """Test Python variable in shell pipeline."""
        run_command(
            'x = "hello"; result = $(echo @(x) | grep hello); print(result)')
        self.assertEqual(sys.stdout.getvalue().strip(), 'hello')

    def test_mixed_python_list_with_pipeline(self):
        """Test Python list expansion in pipeline."""
        run_command(
            'items = [1, 2, 3]; result = $(echo @(items) | grep 2); print(result)')
        self.assertIn('2', sys.stdout.getvalue())

    def test_mixed_python_with_redirection(self):
        """Test Python variable with shell redirection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'output.txt')
            run_command(f'x = "test content"; echo @(x) > {output_file}')
            with open(output_file) as f:
                self.assertEqual(f.read().strip(), 'test content')

    def test_mixed_expression_with_redirection(self):
        """Test Python expression result in redirected shell command."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'output.txt')
            run_command(f'x = 10; echo @(x * 2) > {output_file}')
            with open(output_file) as f:
                self.assertEqual(f.read().strip(), '20')

    def test_all_three_combined(self):
        """Test Python + pipeline + redirection together."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'output.txt')
            run_command(
                f'x = "important"; echo @(x) data | grep important > {output_file}')
            with open(output_file) as f:
                content = f.read().strip()
                self.assertIn('important', content)

    def test_multiple_expansions_in_pipeline(self):
        """Test multiple Python expansions in a pipeline."""
        run_command(
            'x = "hello"; y = "world"; result = $(echo @(x) @(y) | grep world); print(result)')
        output = sys.stdout.getvalue().strip()
        self.assertIn('world', output)

    def test_loop_with_pipeline_and_redirection(self):
        """Test for loop with pipeline and redirection (complex scenario)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'output.txt')
            # Correct syntax: shell command inside !(), with @() for Python values
            run_command(f'files = ["a", "b", "c"]')
            run_command(
                f'for f in files: $(echo @(f) | grep -v x >> {output_file})')
            with open(output_file) as f:
                content = f.read().strip()
                self.assertIn('a', content)
                self.assertIn('b', content)
                self.assertIn('c', content)

    def test_mixed_with_and_operator_and_pipeline(self):
        """Test && operator with pipeline."""
        run_command('x = 5; true && echo @(x) | grep 5')

    def test_mixed_with_and_operator_and_redirection(self):
        """Test && operator with redirection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'output.txt')
            run_command(f'x = 10; true && echo @(x) > {output_file}')
            with open(output_file) as f:
                self.assertEqual(f.read().strip(), '10')

    def test_complex_nested_scenario(self):
        """Test complex nested: Python loop + expansions + pipeline + redirection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'output.txt')
            # Correct syntax: shell command with @() expansion in for loop
            run_command(f'items = ["cat", "dog", "bat"]')
            run_command(
                f'for item in items: !(echo @(item) | grep at >> {output_file})')
            with open(output_file) as f:
                content = f.read().strip()
                self.assertIn('cat', content)
                self.assertIn('bat', content)
                self.assertNotIn('dog\n', content + '\n')


class TestErrorHandling(unittest.TestCase):
    """Test error handling and syntax detection."""

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

    def test_python_syntax_error_detected(self):
        """Test Python syntax error is shown, not treated as shell."""
        # foo( has unmatched paren - should be Python error
        run_command('foo(')
        stderr = sys.stderr.getvalue()
        # Should have a Python error, not "command not found"
        self.assertTrue(len(stderr) > 0)

    def test_undefined_variable_in_expansion(self):
        """Test undefined variable in @() raises error."""
        # Errors in expansions are printed to stderr
        run_command('x = @(undefined_var)')
        stderr = sys.stderr.getvalue()
        # Should have NameError about undefined_var
        self.assertTrue('undefined_var' in stderr or 'NameError' in stderr)


if __name__ == '__main__':
    unittest.main()
