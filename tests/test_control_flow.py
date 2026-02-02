from app.parsing import parse_control_flow
from app.core.execution import python_namespace
from app.core import run_command
import unittest
import os
import sys
import tempfile
from io import StringIO
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestControlFlowParsing(unittest.TestCase):
    """Test parsing of &&, ||, and ; operators."""

    def test_parse_single_command(self):
        """Test parsing command without operators."""
        result = parse_control_flow("echo hello")
        self.assertEqual(result, [(None, "echo hello")])

    def test_parse_and_operator(self):
        """Test parsing && operator."""
        result = parse_control_flow("cmd1 && cmd2")
        self.assertEqual(result, [(None, "cmd1"), ("&&", "cmd2")])

    def test_parse_or_operator(self):
        """Test parsing || operator."""
        result = parse_control_flow("cmd1 || cmd2")
        self.assertEqual(result, [(None, "cmd1"), ("||", "cmd2")])

    def test_parse_semicolon(self):
        """Test parsing ; operator."""
        result = parse_control_flow("cmd1 ; cmd2")
        self.assertEqual(result, [(None, "cmd1"), (";", "cmd2")])

    def test_parse_multiple_and(self):
        """Test parsing multiple && operators."""
        result = parse_control_flow("cmd1 && cmd2 && cmd3")
        self.assertEqual(result, [
            (None, "cmd1"),
            ("&&", "cmd2"),
            ("&&", "cmd3")
        ])

    def test_parse_mixed_operators(self):
        """Test parsing mixed operators."""
        result = parse_control_flow("cmd1 && cmd2 || cmd3 ; cmd4")
        self.assertEqual(result, [
            (None, "cmd1"),
            ("&&", "cmd2"),
            ("||", "cmd3"),
            (";", "cmd4")
        ])

    def test_parse_operators_in_quotes(self):
        """Test that operators in quotes are not parsed."""
        result = parse_control_flow('echo "&&" && echo "test"')
        self.assertEqual(result, [(None, 'echo "&&"'), ("&&", 'echo "test"')])

    def test_parse_operators_in_single_quotes(self):
        """Test that operators in single quotes are not parsed."""
        result = parse_control_flow("echo '||' || echo test")
        self.assertEqual(result, [(None, "echo '||'"), ("||", "echo test")])

    def test_parse_with_pipe(self):
        """Test that pipe | is not confused with ||."""
        result = parse_control_flow("cmd1 | cmd2 && cmd3")
        self.assertEqual(result, [(None, "cmd1 | cmd2"), ("&&", "cmd3")])


class TestAndOperator(unittest.TestCase):
    """Test && operator behavior."""

    def setUp(self):
        """Redirect stdout for testing."""
        self.old_stdout = sys.stdout
        sys.stdout = StringIO()

    def tearDown(self):
        """Restore stdout."""
        sys.stdout = self.old_stdout

    def test_and_both_succeed(self):
        """Test && when both commands succeed."""
        run_command('echo "first" && echo "second"')
        output = sys.stdout.getvalue()
        self.assertIn("first", output)
        self.assertIn("second", output)

    def test_and_first_fails(self):
        """Test && when first command fails - second should not run."""
        run_command('false && echo "should not appear"')
        output = sys.stdout.getvalue()
        self.assertNotIn("should not appear", output)

    def test_and_cd_success(self):
        """Test && with successful cd."""
        original_dir = os.getcwd()
        try:
            run_command('cd /tmp && pwd')
            output = sys.stdout.getvalue()
            self.assertIn("/tmp", output)
        finally:
            os.chdir(original_dir)

    def test_and_cd_failure(self):
        """Test && when cd fails."""
        run_command('cd /nonexistent_directory_xyz && echo "should not appear"')
        output = sys.stdout.getvalue()
        self.assertNotIn("should not appear", output)

    def test_and_type_success(self):
        """Test && with type finding command."""
        run_command('type echo && echo "found"')
        output = sys.stdout.getvalue()
        self.assertIn("found", output)

    def test_and_type_failure(self):
        """Test && when type doesn't find command."""
        run_command('type notacommandxyz && echo "should not appear"')
        output = sys.stdout.getvalue()
        self.assertNotIn("should not appear", output)

    def test_and_chain(self):
        """Test multiple && operators."""
        run_command('echo "a" && echo "b" && echo "c"')
        output = sys.stdout.getvalue()
        self.assertIn("a", output)
        self.assertIn("b", output)
        self.assertIn("c", output)

    def test_and_chain_breaks(self):
        """Test && chain breaks on first failure."""
        run_command('echo "a" && false && echo "should not appear"')
        output = sys.stdout.getvalue()
        self.assertIn("a", output)
        self.assertNotIn("should not appear", output)


class TestOrOperator(unittest.TestCase):
    """Test || operator behavior."""

    def setUp(self):
        """Redirect stdout for testing."""
        self.old_stdout = sys.stdout
        sys.stdout = StringIO()

    def tearDown(self):
        """Restore stdout."""
        sys.stdout = self.old_stdout

    def test_or_first_succeeds(self):
        """Test || when first command succeeds - second should not run."""
        run_command('true || echo "should not appear"')
        output = sys.stdout.getvalue()
        self.assertNotIn("should not appear", output)

    def test_or_first_fails(self):
        """Test || when first command fails - second should run."""
        run_command('false || echo "fallback"')
        output = sys.stdout.getvalue()
        self.assertIn("fallback", output)

    def test_or_command_not_found(self):
        """Test || with command not found."""
        run_command('/nonexistent/command || echo "fallback executed"')
        output = sys.stdout.getvalue()
        self.assertIn("fallback executed", output)

    def test_or_chain(self):
        """Test multiple || operators."""
        run_command('false || false || echo "third"')
        output = sys.stdout.getvalue()
        self.assertIn("third", output)


class TestSemicolon(unittest.TestCase):
    """Test ; operator behavior."""

    def setUp(self):
        """Redirect stdout for testing."""
        self.old_stdout = sys.stdout
        sys.stdout = StringIO()

    def tearDown(self):
        """Restore stdout."""
        sys.stdout = self.old_stdout

    def test_semicolon_always_runs(self):
        """Test ; always runs next command."""
        run_command('false ; echo "this always runs"')
        output = sys.stdout.getvalue()
        self.assertIn("this always runs", output)

    def test_semicolon_multiple(self):
        """Test multiple ; operators."""
        run_command('echo "a" ; echo "b" ; echo "c"')
        output = sys.stdout.getvalue()
        self.assertIn("a", output)
        self.assertIn("b", output)
        self.assertIn("c", output)


class TestMixedOperators(unittest.TestCase):
    """Test combinations of &&, ||, and ;."""

    def setUp(self):
        """Redirect stdout for testing."""
        self.old_stdout = sys.stdout
        sys.stdout = StringIO()

    def tearDown(self):
        """Restore stdout."""
        sys.stdout = self.old_stdout

    def test_and_then_or(self):
        """Test && followed by ||."""
        run_command('true && echo "yes" || echo "no"')
        output = sys.stdout.getvalue()
        self.assertIn("yes", output)
        self.assertNotIn("no", output)

    def test_fail_and_or_recovery(self):
        """Test || recovery after && failure."""
        run_command('false || echo "recovered" && echo "continuing"')
        output = sys.stdout.getvalue()
        self.assertIn("recovered", output)
        self.assertIn("continuing", output)

    def test_complex_chain(self):
        """Test complex chain of operators."""
        run_command(
            'echo "start" && false && echo "skip1" || echo "fallback" ; echo "end"')
        output = sys.stdout.getvalue()
        self.assertIn("start", output)
        self.assertNotIn("skip1", output)
        self.assertIn("fallback", output)
        self.assertIn("end", output)


class TestSubstitutionWithControlFlow(unittest.TestCase):
    """Test $() and @() substitutions with control flow operators."""

    def setUp(self):
        """Redirect stdout and clear namespace."""
        self.old_stdout = sys.stdout
        sys.stdout = StringIO()
        keys_to_remove = [k for k in python_namespace.keys()
                          if not k.startswith('__') and k not in ('CommandResult',)]
        for k in keys_to_remove:
            del python_namespace[k]

    def tearDown(self):
        """Restore stdout."""
        sys.stdout = self.old_stdout

    def test_dollar_substitution_not_executed_on_and_short_circuit(self):
        """Test $() is NOT executed when && short-circuits."""
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "marker.txt"
            # This should NOT create the file because false short-circuits
            run_command(
                f'false && result = $(echo "test" > {marker} && echo "done")')
            self.assertFalse(
                marker.exists(), "Substitution should not have executed")

    def test_dollar_substitution_executed_on_and_success(self):
        """Test $() IS executed when && continues."""
        run_command('x = $(echo "test")')
        self.assertIn('x', python_namespace)
        self.assertEqual(python_namespace['x'], 'test')

    def test_dollar_substitution_not_executed_on_or_short_circuit(self):
        """Test $() is NOT executed when || short-circuits."""
        with tempfile.TemporaryDirectory() as tmpdir:
            marker = Path(tmpdir) / "marker2.txt"
            # This should NOT create the file because true short-circuits
            run_command(
                f'true || result = $(echo "test" > {marker} && echo "done")')
            self.assertFalse(
                marker.exists(), "Substitution should not have executed")

    def test_dollar_substitution_executed_on_or_failure(self):
        """Test $() IS executed when || continues."""
        run_command('false || y = $(echo "fallback")')
        self.assertIn('y', python_namespace)
        self.assertEqual(python_namespace['y'], 'fallback')

    def test_at_substitution_not_executed_on_and_short_circuit(self):
        """Test @() is NOT executed when && short-circuits."""
        run_command('counter = 0')
        run_command('false && echo @(counter := counter + 1)')
        self.assertEqual(
            python_namespace['counter'], 0, "@() should not have executed")

    def test_at_substitution_executed_on_and_success(self):
        """Test @() IS executed when && continues."""
        run_command('x = 100')
        run_command('true && echo @(x * 2)')
        output = sys.stdout.getvalue()
        self.assertIn("200", output)

    def test_at_substitution_not_executed_on_or_short_circuit(self):
        """Test @() is NOT executed when || short-circuits."""
        run_command('counter = 0')
        run_command('true || echo @(counter := counter + 1)')
        self.assertEqual(
            python_namespace['counter'], 0, "@() should not have executed")

    def test_at_substitution_executed_on_or_failure(self):
        """Test @() IS executed when || continues."""
        run_command('x = 100')
        run_command('false || echo @(x * 2)')
        output = sys.stdout.getvalue()
        self.assertIn("200", output)

    def test_bang_substitution_not_executed_on_short_circuit(self):
        """Test !() is NOT executed when && short-circuits."""
        run_command('false && result = !(echo "SHOULD_NOT_RUN")')
        self.assertNotIn('result', python_namespace,
                         "!() should not have executed")

    def test_bang_substitution_executed_on_success(self):
        """Test !() IS executed when && continues."""
        run_command('true && result = !(echo "SHOULD_RUN")')
        self.assertIn('result', python_namespace)
        self.assertEqual(python_namespace['result'].stdout, 'SHOULD_RUN\n')

    def test_multiple_substitutions_in_chain(self):
        """Test multiple substitutions in a chain."""
        run_command('x = 10')
        run_command(
            'true && echo @(x) && echo $(echo "shell") && false && echo @(x * 2)')
        output = sys.stdout.getvalue()
        self.assertIn("10", output)
        self.assertIn("shell", output)
        self.assertNotIn("20", output)  # Should not execute after false


class TestPipelineWithControlFlow(unittest.TestCase):
    """Test pipelines combined with &&, ||, and ; operators."""

    def setUp(self):
        """Redirect stdout."""
        self.old_stdout = sys.stdout
        sys.stdout = StringIO()

    def tearDown(self):
        """Restore stdout."""
        sys.stdout = self.old_stdout

    def test_pipe_then_and(self):
        """Test pipeline followed by &&."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "out.txt"
            run_command(
                f'echo "hello" | grep "h" > {out_file} && echo "found"')
            pipe_output = out_file.read_text()
            stdout_output = sys.stdout.getvalue()
            self.assertIn("hello", pipe_output)
            self.assertIn("found", stdout_output)

    def test_pipe_fail_then_and(self):
        """Test failed pipeline with &&."""
        run_command('echo "hello" | grep "x" && echo "should not appear"')
        output = sys.stdout.getvalue()
        self.assertNotIn("should not appear", output)

    def test_pipe_then_or(self):
        """Test successful pipeline with ||."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "out.txt"
            run_command(f'echo "test" | cat > {out_file} || echo "fallback"')
            pipe_output = out_file.read_text()
            stdout_output = sys.stdout.getvalue()
            self.assertIn("test", pipe_output)
            self.assertNotIn("fallback", stdout_output)

    def test_pipe_fail_then_or(self):
        """Test failed pipeline with ||."""
        run_command('echo "test" | grep "nomatch" || echo "fallback"')
        output = sys.stdout.getvalue()
        self.assertIn("fallback", output)

    def test_and_then_pipe(self):
        """Test && followed by pipeline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "out.txt"
            run_command(f'true && echo "data" | grep "data" > {out_file}')
            output = out_file.read_text()
            self.assertIn("data", output)

    def test_or_then_pipe(self):
        """Test || followed by pipeline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "out.txt"
            run_command(f'false || echo "data" | cat > {out_file}')
            output = out_file.read_text()
            self.assertIn("data", output)


class TestPipelineSubstitutionControlFlow(unittest.TestCase):
    """Test combinations of pipes, substitutions, and control flow operators."""

    def setUp(self):
        """Redirect stdout and clear namespace."""
        self.old_stdout = sys.stdout
        sys.stdout = StringIO()
        keys_to_remove = [k for k in python_namespace.keys()
                          if not k.startswith('__') and k not in ('CommandResult',)]
        for k in keys_to_remove:
            del python_namespace[k]

    def tearDown(self):
        """Restore stdout."""
        sys.stdout = self.old_stdout

    def test_pipe_with_dollar_substitution_and_and(self):
        """Test pipeline with $() substitution and &&."""
        run_command('x = $(echo "test" | cat)')
        run_command('true && echo @(x)')
        output = sys.stdout.getvalue()
        self.assertIn("test", output)

    def test_dollar_substitution_in_pipe_with_and(self):
        """Test $() in pipeline followed by &&."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "out.txt"
            run_command(
                f'echo $(echo "data") | cat > {out_file} && echo "success"')
            pipe_output = out_file.read_text()
            stdout_output = sys.stdout.getvalue()
            self.assertIn("data", pipe_output)
            self.assertIn("success", stdout_output)

    def test_at_substitution_in_pipe_with_or(self):
        """Test @() in pipeline followed by ||."""
        run_command('items = ["a", "b", "c"]')
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "out.txt"
            run_command(
                f'echo @(items) | grep "b" > {out_file} || echo "not found"')
            pipe_output = out_file.read_text()
            stdout_output = sys.stdout.getvalue()
            self.assertIn("a b c", pipe_output)
            self.assertNotIn("not found", stdout_output)

    def test_complex_pipe_substitution_chain(self):
        """Test complex chain with pipes, substitutions, and operators."""
        run_command('x = 100')
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "out.txt"
            run_command(
                f'echo @(x) | grep "100" > {out_file} && result = $(echo "found") || echo "missed"')
            pipe_output = out_file.read_text()
            self.assertIn("100", pipe_output)
            self.assertIn('result', python_namespace)
            self.assertEqual(python_namespace['result'], 'found')

    def test_pipe_fails_substitution_skipped(self):
        """Test that substitution after && is skipped when pipe fails."""
        run_command('counter = 0')
        run_command(
            'echo "test" | grep "nomatch" && echo @(counter := counter + 1)')
        self.assertEqual(
            python_namespace['counter'], 0, "Substitution should not execute")

    def test_pipe_with_substitution_or_recovery(self):
        """Test || recovery with substitution after failed pipe."""
        run_command('y = 50')
        run_command('echo "data" | grep "nomatch" || echo @(y * 2)')
        output = sys.stdout.getvalue()
        self.assertIn("100", output)

    def test_semicolon_with_pipe_and_substitution(self):
        """Test ; with pipes and substitutions."""
        run_command('x = 10')
        with tempfile.TemporaryDirectory() as tmpdir:
            out_file = Path(tmpdir) / "out.txt"
            run_command(f'echo @(x) | cat > {out_file} ; echo "always runs"')
            pipe_output = out_file.read_text()
            stdout_output = sys.stdout.getvalue()
            self.assertIn("10", pipe_output)
            self.assertIn("always runs", stdout_output)

    def test_nested_substitution_pipe_and_chain(self):
        """Test nested $(pipeline) with && chain."""
        run_command('result = $(echo "a b c" | grep "b")')
        run_command('true && echo @(result)')
        output = sys.stdout.getvalue()
        self.assertIn("a b c", output)


if __name__ == '__main__':
    unittest.main()
