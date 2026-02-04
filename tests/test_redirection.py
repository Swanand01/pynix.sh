"""Tests for redirections in shell and mixed contexts."""

from app.core import run_command
from app.core.python.namespace import python_namespace
import unittest
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestRedirections(unittest.TestCase):
    """Test redirections in shell and mixed contexts."""

    def setUp(self):
        """Clear namespace."""
        keys_to_remove = [k for k in python_namespace.keys()
                          if not k.startswith('_') and k not in ('__name__', '__builtins__', 'CommandResult')]
        for k in keys_to_remove:
            del python_namespace[k]

    def test_shell_redirect_stdout(self):
        """Test redirecting stdout to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'output.txt')
            run_command(f'echo test > {output_file}')
            with open(output_file) as f:
                self.assertEqual(f.read().strip(), 'test')

    def test_shell_redirect_append(self):
        """Test appending to file with >>."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, 'output.txt')
            run_command(f'echo first > {output_file}')
            run_command(f'echo second >> {output_file}')
            with open(output_file) as f:
                content = f.read().strip()
                self.assertIn('first', content)
                self.assertIn('second', content)


if __name__ == '__main__':
    unittest.main()
