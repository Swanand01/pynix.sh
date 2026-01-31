import unittest
import os
import sys
import tempfile
from pathlib import Path
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import execute_python, is_python_code
from app.types import CommandResult
from app.core.execution import python_namespace, has_substitution
from app.core.substitution import find_substitutions, find_matching_paren


class TestShellSubstitution(unittest.TestCase):
    """Test $() and !() shell substitution operators."""

    def setUp(self):
        """Clear user-defined variables from namespace before each test."""
        keys_to_remove = [k for k in python_namespace.keys()
                         if not k.startswith('__') and k not in ('CommandResult',)]
        for k in keys_to_remove:
            del python_namespace[k]

    def test_has_substitution_dollar(self):
        """Test detecting $() substitution."""
        self.assertTrue(has_substitution('x = $(ls)'))
        self.assertTrue(has_substitution('$(pwd)'))
        self.assertTrue(has_substitution('print($(echo hi))'))

    def test_has_substitution_bang(self):
        """Test detecting !() substitution."""
        self.assertTrue(has_substitution('r = !(ls)'))
        self.assertTrue(has_substitution('!(pwd)'))

    def test_has_substitution_none(self):
        """Test that regular commands don't have substitution."""
        self.assertFalse(has_substitution('ls -la'))
        self.assertFalse(has_substitution('echo hello'))
        self.assertFalse(has_substitution('x = 5'))
        self.assertFalse(has_substitution('print("hello")'))

    def test_find_matching_paren_simple(self):
        """Test finding matching parenthesis."""
        self.assertEqual(find_matching_paren('(hello)', 0), 6)
        self.assertEqual(find_matching_paren('()', 0), 1)

    def test_find_matching_paren_nested(self):
        """Test finding matching paren with nesting."""
        self.assertEqual(find_matching_paren('(a(b)c)', 0), 6)
        self.assertEqual(find_matching_paren('((()))', 0), 5)

    def test_find_matching_paren_quotes(self):
        """Test that parens in quotes are ignored."""
        self.assertEqual(find_matching_paren('(a")"b)', 0), 6)
        self.assertEqual(find_matching_paren("(a')'b)", 0), 6)

    def test_find_substitutions_single(self):
        """Test finding a single substitution."""
        subs = find_substitutions('x = $(echo hello)')
        self.assertEqual(len(subs), 1)
        start, end, op, cmd = subs[0]
        self.assertEqual(op, '$')
        self.assertEqual(cmd, 'echo hello')

    def test_find_substitutions_bang(self):
        """Test finding !() substitution."""
        subs = find_substitutions('r = !(ls -la)')
        self.assertEqual(len(subs), 1)
        start, end, op, cmd = subs[0]
        self.assertEqual(op, '!')
        self.assertEqual(cmd, 'ls -la')

    def test_find_substitutions_with_pipe(self):
        """Test finding substitution containing pipe."""
        subs = find_substitutions('x = $(ls | wc -l)')
        self.assertEqual(len(subs), 1)
        _, _, op, cmd = subs[0]
        self.assertEqual(cmd, 'ls | wc -l')

    def test_find_substitutions_multiple(self):
        """Test finding multiple substitutions."""
        subs = find_substitutions('$(cmd1) and $(cmd2)')
        self.assertEqual(len(subs), 2)

    def test_dollar_substitution_simple(self):
        """Test $() returns stripped stdout string."""
        execute_python('result = $(echo hello)')
        self.assertIn('result', python_namespace)
        self.assertEqual(python_namespace['result'], 'hello')
        self.assertIsInstance(python_namespace['result'], str)

    def test_dollar_substitution_with_pipe(self):
        """Test $() with pipeline."""
        execute_python('result = $(echo hello world | grep world)')
        self.assertEqual(python_namespace['result'], 'hello world')

    def test_dollar_substitution_pwd(self):
        """Test $() with pwd command."""
        execute_python('cwd = $(pwd)')
        self.assertEqual(python_namespace['cwd'], os.getcwd())

    def test_bang_substitution_simple(self):
        """Test !() returns CommandResult object."""
        execute_python('result = !(echo hello)')
        self.assertIn('result', python_namespace)
        result = python_namespace['result']
        self.assertIsInstance(result, CommandResult)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, 'hello\n')
        self.assertEqual(result.stderr, '')

    def test_bang_substitution_failure(self):
        """Test !() with failing command."""
        execute_python('result = !(ls /nonexistent_dir_xyz)')
        result = python_namespace['result']
        self.assertIsInstance(result, CommandResult)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('nonexistent_dir_xyz', result.stderr)

    def test_bang_substitution_bool(self):
        """Test CommandResult boolean evaluation."""
        execute_python('success = !(echo ok)')
        execute_python('failure = !(ls /nonexistent_xyz)')

        self.assertTrue(bool(python_namespace['success']))
        self.assertFalse(bool(python_namespace['failure']))

    def test_substitution_in_print(self):
        """Test using substitution directly in print."""
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            execute_python('print($(echo inline))')
            output = sys.stdout.getvalue()
            self.assertIn('inline', output)
        finally:
            sys.stdout = old_stdout

    def test_substitution_in_expression(self):
        """Test using substitution in expression."""
        execute_python('length = len($(echo hello))')
        self.assertEqual(python_namespace['length'], 5)

    def test_substitution_with_pipeline_captured(self):
        """Test pipeline capture in substitution."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("apple\nbanana\ncherry\n")

            execute_python(f'result = $(cat {test_file} | grep banana)')
            self.assertEqual(python_namespace['result'], 'banana')

    def test_is_python_code_with_substitution(self):
        """Test that code with substitution is detected as Python."""
        self.assertTrue(is_python_code('x = $(ls)'))
        self.assertTrue(is_python_code('!(pwd)'))
        self.assertTrue(is_python_code('print($(echo hi))'))

    def test_command_result_str(self):
        """Test CommandResult string conversion."""
        execute_python('r = !(echo test)')
        result = python_namespace['r']
        self.assertEqual(str(result), 'test\n')

    def test_command_result_repr(self):
        """Test CommandResult repr."""
        execute_python('r = !(echo test)')
        result = python_namespace['r']
        self.assertIn('CommandResult', repr(result))
        self.assertIn('returncode=0', repr(result))


if __name__ == '__main__':
    unittest.main(verbosity=2)
