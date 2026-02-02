from app.core.substitution import expand, find_expansions, stringify
from app.core.execution import python_namespace
from app.core.runner import run_command
from app.core import execute_python
import unittest
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def run_python(code):
    """Expand and execute Python code (mimics main.py flow)."""
    expanded = expand(code, python_namespace, context='python')
    execute_python(expanded)


def clear_namespace():
    """Clear user-defined variables from namespace."""
    keys_to_remove = [k for k in python_namespace.keys()
                      if not k.startswith('__') and k not in ('CommandResult',)]
    for k in keys_to_remove:
        del python_namespace[k]


class TestPythonInterpolation(unittest.TestCase):
    """Test @() Python interpolation in shell commands."""

    def setUp(self):
        self.namespace = {
            '__builtins__': __builtins__,
            'var': 'hello',
            'num': 42,
            'items': ['a', 'b', 'c'],
        }

    def test_find_expansions_at(self):
        """Test finding @() patterns."""
        expansions = find_expansions('echo @(var)')
        self.assertEqual(len(expansions), 1)
        self.assertEqual(expansions[0][2], '@')
        self.assertEqual(expansions[0][3], 'var')

    def test_quoted_expansions_not_found(self):
        """Test that expansions inside quotes are not expanded."""
        self.assertEqual(find_expansions("echo '@(1+1)'"), [])
        self.assertEqual(find_expansions('echo "@(1+1)"'), [])
        # Mixed: only unquoted expands
        expansions = find_expansions('echo "@(1)" @(2)')
        self.assertEqual(len(expansions), 1)
        self.assertEqual(expansions[0][3], '2')

    def test_expand_simple_variable(self):
        """Test expanding a simple variable."""
        result = expand('echo @(var)', self.namespace, context='shell')
        self.assertEqual(result, 'echo hello')

    def test_expand_expression(self):
        """Test expanding an expression."""
        result = expand('echo @(1 + 2)', self.namespace, context='shell')
        self.assertEqual(result, 'echo 3')

    def test_expand_multiple(self):
        """Test expanding multiple interpolations."""
        result = expand('echo @(var) @(num)', self.namespace, context='shell')
        self.assertEqual(result, 'echo hello 42')

    def test_expand_in_path(self):
        """Test expanding in file path."""
        result = expand('/tmp/@(var).txt', self.namespace, context='shell')
        self.assertEqual(result, '/tmp/hello.txt')

    def test_expand_iterable(self):
        """Test expanding an iterable joins with spaces."""
        result = expand('echo @(items)', self.namespace, context='shell')
        self.assertEqual(result, 'echo a b c')

    def test_expand_range(self):
        """Test expanding a range."""
        result = expand('echo @(range(3))', self.namespace, context='shell')
        self.assertEqual(result, 'echo 0 1 2')

    def test_expand_nested_parens(self):
        """Test expanding expression with nested parentheses."""
        result = expand('echo @(str((1, 2)))', self.namespace, context='shell')
        self.assertEqual(result, 'echo (1, 2)')

    def test_stringify_string(self):
        """Test stringify passes strings through."""
        self.assertEqual(stringify('hello'), 'hello')

    def test_stringify_number(self):
        """Test stringify converts numbers."""
        self.assertEqual(stringify(42), '42')

    def test_stringify_list(self):
        """Test stringify joins lists with spaces."""
        self.assertEqual(stringify(['a', 'b', 'c']), 'a b c')

    def test_stringify_range(self):
        """Test stringify handles range."""
        self.assertEqual(stringify(range(3)), '0 1 2')


class TestNestedExpansion(unittest.TestCase):
    """Test nested expansion: @() containing $() and vice versa."""

    def setUp(self):
        self.namespace = {
            '__builtins__': __builtins__,
            'var': 'hello',
        }

    def test_shell_in_python_in_shell(self):
        """Test @($(echo 5) + 1) - shell inside Python inside shell."""
        result = expand('echo @(int($(echo 5)) + 1)',
                        self.namespace, context='shell')
        self.assertEqual(result, 'echo 6')

    def test_python_in_shell_in_python(self):
        """Test $(echo @(var)) - Python inside shell inside Python."""
        result = expand('x = $(echo @(var))', self.namespace, context='python')
        # After expansion, should have a variable reference
        self.assertIn('__pynix_sub_', result)
        # The namespace should contain the result
        self.assertIn('hello', [str(v) for v in self.namespace.values()])


class TestExpansionErrors(unittest.TestCase):
    """Test error handling in expansions."""

    def setUp(self):
        self.namespace = {'__builtins__': __builtins__}

    def test_undefined_variable(self):
        """Test error on undefined variable."""
        with self.assertRaises(ValueError) as ctx:
            expand('echo @(undefined_var)', self.namespace, context='shell')
        self.assertIn('undefined_var', str(ctx.exception))

    def test_syntax_error(self):
        """Test error on syntax error in expression."""
        with self.assertRaises(ValueError):
            expand('echo @(1 +)', self.namespace, context='shell')


class TestPipesWithExpansion(unittest.TestCase):
    """Test pipes combined with expansion operators."""

    def setUp(self):
        self.namespace = {'__builtins__': __builtins__}

    def test_at_expansion_with_pipe(self):
        """Test @() in a pipeline command."""
        result = expand('echo @(2+2) | cat', self.namespace, context='shell')
        self.assertEqual(result, 'echo 4 | cat')

    def test_dollar_expansion_with_pipe(self):
        """Test $() containing a pipeline."""
        result = expand('x = $(echo hello | tr a-z A-Z)',
                        self.namespace, context='python')
        self.assertIn('__pynix_sub_', result)
        subst_val = [v for k, v in self.namespace.items()
                     if k.startswith('__pynix_sub_')]
        self.assertEqual(subst_val[0], 'HELLO')

    def test_special_chars_in_pipe(self):
        """Test special characters (newlines) preserved in pipeline capture."""
        result = expand('x = $(echo "a b c" | tr " " "\n")',
                        self.namespace, context='python')
        subst_val = [v for k, v in self.namespace.items()
                     if k.startswith('__pynix_sub_')]
        self.assertEqual(subst_val[0], 'a\nb\nc')

    def test_multiple_at_expansions_with_pipe(self):
        """Test multiple @() in a pipeline."""
        result = expand('echo @(1+1) @(2+2) | cat',
                        self.namespace, context='shell')
        self.assertEqual(result, 'echo 2 4 | cat')


class TestMixedOperators(unittest.TestCase):
    """Test multiple different operators in the same command."""

    def setUp(self):
        self.namespace = {'__builtins__': __builtins__}

    def test_at_with_dollar_nested(self):
        """Test @(len($(pwd))) - $ inside @."""
        result = expand('echo @(len($(pwd)))', self.namespace, context='shell')
        self.assertEqual(result, f'echo {len(os.getcwd())}')

    def test_dollar_and_at_separate(self):
        """Test $() and @() as separate expansions in Python context."""
        self.namespace['x'] = 10
        result = expand('y = $(echo 5) + str(@(x))',
                        self.namespace, context='python')
        self.assertIn('__pynix_sub_', result)

    def test_bang_with_at(self):
        """Test !() result used with @()."""
        # Expand and execute to get 'r' in namespace
        expanded = expand('r = !(echo test)', self.namespace, context='python')
        exec(expanded, self.namespace)
        # Now use r.returncode in @()
        result = expand('echo @(r.returncode)',
                        self.namespace, context='shell')
        self.assertEqual(result, 'echo 0')


class TestRunCommandIntegration(unittest.TestCase):
    """Integration tests for the full run_command flow."""

    def setUp(self):
        clear_namespace()

    def test_run_python_with_substitution(self):
        """Test run_command with Python code containing $()."""
        run_command('result = $(echo hello)')
        self.assertEqual(python_namespace.get('result'), 'hello')

    def test_run_nested_expansion(self):
        """Test run_command with nested expansions."""
        run_command('length = len($(pwd))')
        self.assertEqual(python_namespace.get('length'), len(os.getcwd()))

    def test_run_pipeline_with_capture(self):
        """Test run_command with pipeline inside $()."""
        run_command('upper = $(echo hello | tr a-z A-Z)')
        self.assertEqual(python_namespace.get('upper'), 'HELLO')

    def test_run_bang_substitution(self):
        """Test run_command with !() substitution."""
        run_command('r = !(echo test)')
        self.assertEqual(python_namespace['r'].returncode, 0)
        self.assertEqual(python_namespace['r'].stdout, 'test\n')

    def test_run_mixed_operators(self):
        """Test run_command with both $ and @ operators."""
        run_command('x = len($(pwd)) + 1')
        self.assertEqual(python_namespace.get('x'), len(os.getcwd()) + 1)


class TestComprehensiveIntegration(unittest.TestCase):
    """Comprehensive tests mixing Python, shell, pipes, and redirection."""

    def setUp(self):
        clear_namespace()
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir)

    def test_python_var_in_shell_pipeline_with_redirect(self):
        """Test @() in shell pipeline with file redirection."""
        outfile = os.path.join(self.tmpdir, 'out.txt')
        run_command('count = 3')
        run_command(f'echo @(count) | cat > {outfile}')
        with open(outfile) as f:
            self.assertEqual(f.read().strip(), '3')

    def test_capture_pipeline_into_python_var(self):
        """Test $() capturing pipeline output into Python variable."""
        run_command('result = $(echo "hello world" | tr a-z A-Z)')
        self.assertEqual(python_namespace.get('result'), 'HELLO WORLD')

    def test_bang_capture_with_stderr_redirect(self):
        """Test !() capturing command with stderr."""
        errfile = os.path.join(self.tmpdir, 'err.txt')
        run_command(f'r = !(ls /nonexistent 2> {errfile})')
        self.assertNotEqual(python_namespace['r'].returncode, 0)

    def test_mixed_operators_with_pipeline(self):
        """Test both @() and $() in pipeline context."""
        run_command('prefix = "test"')
        run_command('out = $(echo @(prefix) | tr a-z A-Z)')
        self.assertEqual(python_namespace.get('out'), 'TEST')

    def test_nested_expansion_with_redirect(self):
        """Test nested $() with file output."""
        outfile = os.path.join(self.tmpdir, 'nested.txt')
        run_command('x = 5')
        run_command(f'echo $(echo @(x * 2)) > {outfile}')
        with open(outfile) as f:
            self.assertEqual(f.read().strip(), '10')

    def test_stdout_stderr_separate_files(self):
        """Test redirecting stdout and stderr to separate files."""
        outfile = os.path.join(self.tmpdir, 'stdout.txt')
        errfile = os.path.join(self.tmpdir, 'stderr.txt')
        # Use a command that produces both stdout and stderr
        run_command(f'echo out > {outfile} 2> {errfile}')
        with open(outfile) as f:
            self.assertEqual(f.read().strip(), 'out')

    def test_pipeline_with_python_expression(self):
        """Test pipeline using Python list comprehension result."""
        run_command('nums = [1, 2, 3]')
        run_command(
            'result = $(echo @(" ".join(str(n) for n in nums)) | tr " " "\\n" | sort -r)')
        self.assertEqual(python_namespace.get('result'), '3\n2\n1')

    def test_full_integration(self):
        """Command with @(), pipe, stdout redirect, and stderr redirect."""
        outfile = os.path.join(self.tmpdir, 'out.txt')
        errfile = os.path.join(self.tmpdir, 'err.txt')

        run_command('msg = "hello"')
        run_command(f'echo @(msg) | tr a-z A-Z > {outfile} 2> {errfile}')

        with open(outfile) as f:
            self.assertEqual(f.read().strip(), 'HELLO')
        self.assertTrue(os.path.exists(errfile))


if __name__ == '__main__':
    unittest.main(verbosity=2)
