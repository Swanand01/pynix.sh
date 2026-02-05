"""Tests for builtin commands."""

from app.core import run_command
from app.core.python.namespace import python_namespace
import unittest
import sys
import os
import tempfile
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBuiltinCommands(unittest.TestCase):
    """Test builtin commands."""

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

    def test_builtin_pwd(self):
        """Test pwd builtin."""
        # Ensure we're in a valid directory (test isolation issue)
        project_root = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__)))
        os.chdir(project_root)
        # pwd executes successfully - just check returncode
        run_command('result = !(pwd)')
        self.assertIn('result', python_namespace)
        self.assertEqual(python_namespace['result'].returncode, 0)

    def test_builtin_cd(self):
        """Test cd builtin."""
        original_dir = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                run_command(f'cd {tmpdir}')
                # Use realpath to handle symlinks (/var vs /private/var on macOS)
                self.assertEqual(os.path.realpath(os.getcwd()),
                                 os.path.realpath(tmpdir))
        finally:
            # Restore original directory so subsequent tests don't fail
            os.chdir(original_dir)

    def test_builtin_true(self):
        """Test true builtin returns success."""
        run_command('result = !(true)')
        self.assertIn('result', python_namespace)
        self.assertEqual(python_namespace['result'].returncode, 0)

    def test_builtin_false(self):
        """Test false builtin returns failure."""
        run_command('result = !(false)')
        self.assertIn('result', python_namespace)
        self.assertEqual(python_namespace['result'].returncode, 1)

    def test_true_with_and_operator(self):
        """Test true && echo succeeds and runs echo."""
        run_command('true && echo success')
        output = sys.stdout.getvalue()
        self.assertIn('success', output)

    def test_false_with_and_operator(self):
        """Test false && echo fails and skips echo."""
        run_command('false && echo should_not_appear')
        output = sys.stdout.getvalue()
        self.assertNotIn('should_not_appear', output)

    def test_true_with_or_operator(self):
        """Test true || echo succeeds and skips echo."""
        run_command('true || echo should_not_appear')
        output = sys.stdout.getvalue()
        self.assertNotIn('should_not_appear', output)

    def test_false_with_or_operator(self):
        """Test false || echo fails and runs echo."""
        run_command('false || echo fallback')
        output = sys.stdout.getvalue()
        self.assertIn('fallback', output)


if __name__ == '__main__':
    unittest.main()
