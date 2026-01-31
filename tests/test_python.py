import unittest
import os
import sys
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core import execute_python, is_python_code
from app.core.execution import is_python_name, python_namespace


class TestPythonExecution(unittest.TestCase):
    """Test Python code execution and detection."""

    def setUp(self):
        """Clear user-defined variables from namespace before each test."""
        keys_to_remove = [k for k in python_namespace.keys()
                         if not k.startswith('_') and k not in ('__name__', '__builtins__', 'CommandResult')]
        for k in keys_to_remove:
            del python_namespace[k]

    def test_is_python_code_assignment(self):
        """Test detecting Python assignments."""
        self.assertTrue(is_python_code('x = 5'))
        self.assertTrue(is_python_code('ls = 2'))
        self.assertTrue(is_python_code('my_var = "hello"'))

    def test_is_python_code_shell_command(self):
        """Test detecting shell commands."""
        self.assertFalse(is_python_code('ls'))
        self.assertFalse(is_python_code('ls -la'))
        self.assertFalse(is_python_code('grep test'))
        self.assertFalse(is_python_code('cat file.txt'))

    def test_is_python_code_expression(self):
        """Test detecting Python expressions with literals."""
        self.assertTrue(is_python_code('2 + 2'))
        self.assertTrue(is_python_code('[1, 2, 3]'))
        self.assertTrue(is_python_code('{"a": 1}'))

    def test_is_python_code_builtin_calls(self):
        """Test detecting Python builtin function calls."""
        self.assertTrue(is_python_code('print("hello")'))
        self.assertTrue(is_python_code('len([1, 2, 3])'))
        self.assertTrue(is_python_code('range(10)'))
        self.assertTrue(is_python_code('sum([1, 2, 3])'))

    def test_is_python_name_builtins(self):
        """Test that builtins are recognized as Python names."""
        self.assertTrue(is_python_name('print'))
        self.assertTrue(is_python_name('len'))
        self.assertTrue(is_python_name('range'))
        self.assertTrue(is_python_name('sum'))
        self.assertTrue(is_python_name('int'))
        self.assertTrue(is_python_name('str'))

    def test_is_python_name_unknown(self):
        """Test that unknown names are not recognized."""
        self.assertFalse(is_python_name('unknown_var'))
        self.assertFalse(is_python_name('ls'))
        self.assertFalse(is_python_name('grep'))

    def test_python_execution_print(self):
        """Test executing Python print statement."""
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            execute_python('print("hello")')
            output = sys.stdout.getvalue()
            self.assertIn('hello', output)
        finally:
            sys.stdout = old_stdout

    def test_python_execution_expression_result(self):
        """Test that expression results are printed."""
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            execute_python('2 + 2')
            output = sys.stdout.getvalue()
            self.assertIn('4', output)
        finally:
            sys.stdout = old_stdout

    def test_python_persistent_namespace(self):
        """Test that variables persist across executions."""
        execute_python('test_var = 42')
        self.assertIn('test_var', python_namespace)
        self.assertEqual(python_namespace['test_var'], 42)

        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            execute_python('print(test_var)')
            output = sys.stdout.getvalue()
            self.assertIn('42', output)
        finally:
            sys.stdout = old_stdout

    def test_python_function_definition(self):
        """Test defining and calling functions."""
        execute_python('def double(x): return x * 2')
        self.assertIn('double', python_namespace)

        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            execute_python('print(double(5))')
            output = sys.stdout.getvalue()
            self.assertIn('10', output)
        finally:
            sys.stdout = old_stdout

    def test_python_import(self):
        """Test importing modules."""
        execute_python('import math')
        self.assertIn('math', python_namespace)

        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            execute_python('print(math.pi)')
            output = sys.stdout.getvalue()
            self.assertIn('3.14', output)
        finally:
            sys.stdout = old_stdout

    def test_python_multiline_not_confused_with_shell(self):
        """Test that Python code isn't confused with shell commands."""
        # After assigning 'x', 'x + 1' should be Python
        execute_python('x = 10')
        self.assertTrue(is_python_code('x + 1'))
        self.assertTrue(is_python_code('x'))

    def test_python_syntax_error_handling(self):
        """Test that syntax errors are handled gracefully."""
        old_stderr = sys.stderr
        sys.stderr = StringIO()
        try:
            execute_python('def bad syntax')
            output = sys.stderr.getvalue()
            self.assertIn('SyntaxError', output)
        finally:
            sys.stderr = old_stderr


if __name__ == '__main__':
    unittest.main(verbosity=2)
