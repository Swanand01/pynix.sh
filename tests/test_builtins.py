from app.commands.builtins import (
    handle_echo, handle_pwd, handle_type, handle_cd,
    is_builtin
)
import unittest
import os
import sys
import tempfile
from pathlib import Path
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBuiltinCommands(unittest.TestCase):
    """Test all builtin commands with file object parameters."""

    def test_echo_stdout(self):
        """Test echo writes to custom stdout."""
        f = StringIO()
        handle_echo(['hello', 'world'], stdout=f)
        self.assertEqual(f.getvalue(), 'hello world\n')

    def test_echo_empty(self):
        """Test echo with no arguments."""
        f = StringIO()
        handle_echo([], stdout=f)
        self.assertEqual(f.getvalue(), '\n')

    def test_pwd_stdout(self):
        """Test pwd writes to custom stdout."""
        f = StringIO()
        handle_pwd(stdout=f)
        result = f.getvalue().strip()
        self.assertEqual(result, os.getcwd())

    def test_type_builtin(self):
        """Test type command identifies builtins."""
        f = StringIO()
        handle_type('echo', stdout=f)
        self.assertIn('shell builtin', f.getvalue())

    def test_type_external(self):
        """Test type command identifies external commands."""
        f = StringIO()
        handle_type('ls', stdout=f)
        result = f.getvalue()
        self.assertIn('ls is', result)

    def test_type_not_found(self):
        """Test type command for non-existent command."""
        f = StringIO()
        handle_type('nonexistent_command_xyz', stdout=f)
        self.assertIn('not found', f.getvalue())

    def test_cd_changes_directory(self):
        """Test cd changes the current directory."""
        original_dir = os.getcwd()
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                handle_cd(tmpdir)
                # Use realpath to handle macOS /var -> /private/var symlink
                self.assertEqual(os.path.realpath(
                    os.getcwd()), os.path.realpath(tmpdir))
        finally:
            os.chdir(original_dir)

    def test_cd_home(self):
        """Test cd ~ goes to home directory."""
        original_dir = os.getcwd()
        try:
            handle_cd('~')
            self.assertEqual(os.getcwd(), str(Path.home()))
        finally:
            os.chdir(original_dir)

    def test_is_builtin(self):
        """Test builtin detection."""
        self.assertTrue(is_builtin('echo'))
        self.assertTrue(is_builtin('pwd'))
        self.assertTrue(is_builtin('cd'))
        self.assertTrue(is_builtin('type'))
        self.assertTrue(is_builtin('exit'))
        self.assertFalse(is_builtin('ls'))
        self.assertFalse(is_builtin('grep'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
