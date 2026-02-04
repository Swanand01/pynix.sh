from app.core import run_command
from app.core.python.namespace import python_namespace
import unittest
import sys
import os
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestPythonExecution(unittest.TestCase):
    """Test pure Python code execution."""

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

    def test_python_expression(self):
        """Test Python expression evaluation."""
        run_command('2 + 2')
        self.assertEqual(sys.stdout.getvalue().strip(), '4')

    def test_python_assignment(self):
        """Test Python variable assignment."""
        run_command('x = 42')
        self.assertEqual(python_namespace['x'], 42)

    def test_python_print(self):
        """Test Python print statement."""
        run_command('print("hello world")')
        self.assertEqual(sys.stdout.getvalue().strip(), 'hello world')

    def test_python_for_loop(self):
        """Test Python for loop."""
        run_command('for i in range(3): print(i)')
        lines = sys.stdout.getvalue().strip().split('\n')
        self.assertEqual(lines, ['0', '1', '2'])

    def test_python_function_def(self):
        """Test Python function definition."""
        run_command('def add(a, b): return a + b')
        self.assertIn('add', python_namespace)
        run_command('print(add(3, 4))')
        self.assertIn('7', sys.stdout.getvalue())

    def test_python_list_comprehension(self):
        """Test Python list comprehension."""
        run_command('result = [x*2 for x in range(3)]; print(result)')
        self.assertEqual(sys.stdout.getvalue().strip(), '[0, 2, 4]')

    def test_python_import(self):
        """Test Python import statement."""
        run_command('import math')
        run_command('print(math.pi)')
        self.assertIn('3.14', sys.stdout.getvalue())


if __name__ == '__main__':
    unittest.main()
