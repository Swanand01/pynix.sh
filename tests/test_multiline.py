"""Tests for multiline shell command execution."""

from app.core import run_command
from app.core.python.namespace import python_namespace
from app.core.shell.execution import split_on_unquoted_newlines
import unittest
import sys
import os
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMultiline(unittest.TestCase):
    """Test multiline command execution for both shell and Python."""

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

    # --- Split utility tests ---

    def test_split_simple(self):
        """Test splitting simple multiline command."""
        result = split_on_unquoted_newlines("echo hi\nls")
        self.assertEqual(result, ["echo hi", "ls"])

    def test_split_no_newline(self):
        """Test command without newlines."""
        result = split_on_unquoted_newlines("echo hello")
        self.assertEqual(result, ["echo hello"])

    def test_split_multiple_newlines(self):
        """Test multiple newlines."""
        result = split_on_unquoted_newlines("echo a\necho b\necho c")
        self.assertEqual(result, ["echo a", "echo b", "echo c"])

    def test_split_newline_in_double_quotes(self):
        """Test newline inside double quotes is preserved."""
        result = split_on_unquoted_newlines('echo "hello\nworld"')
        self.assertEqual(result, ['echo "hello\nworld"'])

    def test_split_newline_in_single_quotes(self):
        """Test newline inside single quotes is preserved."""
        result = split_on_unquoted_newlines("echo 'hello\nworld'")
        self.assertEqual(result, ["echo 'hello\nworld'"])

    def test_split_mixed_quoted_unquoted(self):
        """Test mix of quoted and unquoted newlines."""
        result = split_on_unquoted_newlines('echo "a\nb"\necho c')
        self.assertEqual(result, ['echo "a\nb"', 'echo c'])

    def test_split_empty_lines(self):
        """Test handling of empty lines."""
        result = split_on_unquoted_newlines("echo a\n\necho b")
        self.assertEqual(result, ["echo a", "", "echo b"])

    # --- Multiline shell execution tests ---

    def test_shell_multiline_echo(self):
        """Test multiple echo commands on separate lines."""
        run_command("echo hello\necho world")
        output = sys.stdout.getvalue()
        self.assertIn('hello', output)
        self.assertIn('world', output)

    def test_shell_multiline_different_commands(self):
        """Test different commands on separate lines."""
        run_command("echo test\npwd")
        output = sys.stdout.getvalue()
        self.assertIn('test', output)

    def test_shell_multiline_with_pipeline(self):
        """Test multiline with pipeline in one line."""
        run_command("echo hello | grep h\necho done")
        output = sys.stdout.getvalue()
        self.assertIn('done', output)

    def test_shell_multiline_capture_stdout(self):
        """Test capturing stdout from multiline commands."""
        run_command('result = $( echo line1\necho line2 ); print(result)')
        output = sys.stdout.getvalue()
        self.assertIn('line1', output)
        self.assertIn('line2', output)

    def test_shell_multiline_capture_full(self):
        """Test capturing full result from multiline commands."""
        run_command('result = !( echo test\necho test2 )')
        self.assertIn('result', python_namespace)
        self.assertEqual(python_namespace['result'].returncode, 0)
        self.assertIn('test', python_namespace['result'].stdout)

    def test_shell_multiline_with_interpolation(self):
        """Test multiline shell with @() interpolation."""
        run_command('x = 5')
        run_command('echo @(x * 2)\necho done')
        output = sys.stdout.getvalue()
        self.assertIn('10', output)
        self.assertIn('done', output)

    def test_shell_multiline_python_then_shell(self):
        """Test Python assignment then multiline shell."""
        run_command(
            'name = "world"\nprint($(echo hello @(name)))\nprint($(echo goodbye))')
        output = sys.stdout.getvalue()
        self.assertIn('hello world', output)
        self.assertIn('goodbye', output)

    def test_shell_multiline_preserves_quoted_newlines(self):
        """Test that newlines in quotes are preserved."""
        run_command('echo "line1\nline2"')
        output = sys.stdout.getvalue()
        self.assertIn('line1', output)

    def test_shell_multiline_with_and_operator(self):
        """Test multiline combined with && operator."""
        run_command("echo first && echo second\necho third")
        output = sys.stdout.getvalue()
        self.assertIn('first', output)
        self.assertIn('second', output)
        self.assertIn('third', output)

    def test_shell_multiline_with_semicolon(self):
        """Test multiline combined with semicolon."""
        run_command("echo a; echo b\necho c")
        output = sys.stdout.getvalue()
        self.assertIn('a', output)
        self.assertIn('b', output)
        self.assertIn('c', output)

    def test_shell_multiline_three_commands(self):
        """Test three commands on separate lines."""
        run_command("echo one\necho two\necho three")
        output = sys.stdout.getvalue()
        self.assertIn('one', output)
        self.assertIn('two', output)
        self.assertIn('three', output)

    def test_shell_multiline_with_builtin(self):
        """Test multiline with builtin command."""
        run_command("echo before\npwd\necho after")
        output = sys.stdout.getvalue()
        self.assertIn('before', output)
        self.assertIn('after', output)

    # --- Multiline Python preserved tests ---

    def test_python_multiline_function(self):
        """Test multiline Python function definition."""
        run_command("def greet(name):\n    return f'Hello, {name}!'")
        self.assertIn('greet', python_namespace)
        self.assertEqual(python_namespace['greet']('World'), 'Hello, World!')

    def test_python_multiline_loop(self):
        """Test multiline Python for loop."""
        run_command("total = 0\nfor i in range(3):\n    total += i")
        self.assertIn('total', python_namespace)
        self.assertEqual(python_namespace['total'], 3)

    def test_python_multiline_if(self):
        """Test multiline Python if statement."""
        run_command(
            "x = 10\nif x > 5:\n    result = 'big'\nelse:\n    result = 'small'")
        self.assertIn('result', python_namespace)
        self.assertEqual(python_namespace['result'], 'big')

    def test_python_multiline_class(self):
        """Test multiline Python class definition."""
        run_command(
            "class Counter:\n    def __init__(self):\n        self.count = 0")
        self.assertIn('Counter', python_namespace)

    def test_python_multiline_list_comprehension(self):
        """Test multiline that results in list comprehension."""
        run_command("nums = [1, 2, 3]\nsquares = [x**2 for x in nums]")
        self.assertIn('squares', python_namespace)
        self.assertEqual(python_namespace['squares'], [1, 4, 9])


if __name__ == '__main__':
    unittest.main()
