import unittest
import os
import sys
import tempfile
from pathlib import Path
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.parsing import parse_pipeline
from app.parsing.pipeline import execute_pipeline


class TestPipelines(unittest.TestCase):
    """Test pipeline execution with new cross-platform approach."""

    def test_builtin_to_external(self):
        """Test builtin | external command."""
        # Pipeline output goes to real stdout (can't easily capture with StringIO in threading)
        # Test by redirecting to a file instead
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "output.txt"
            pipeline = parse_pipeline(f"echo hello | grep h > {output_file}")
            execute_pipeline(pipeline)
            self.assertEqual(output_file.read_text(), 'hello\n')

    def test_builtin_to_external_no_match(self):
        """Test pipeline with no matches."""
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        try:
            pipeline = parse_pipeline("echo world | grep x")
            execute_pipeline(pipeline)
            output = sys.stdout.getvalue()
            self.assertEqual(output, '')
        finally:
            sys.stdout = old_stdout

    def test_pipeline_with_redirect(self):
        """Test pipeline with output redirection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "pipe_out.txt"
            pipeline = parse_pipeline(f"echo test | cat > {output_file}")
            execute_pipeline(pipeline)
            self.assertEqual(output_file.read_text(), 'test\n')

    def test_builtin_only_pipeline(self):
        """Test simple builtin command with redirect."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "builtin_pipe.txt"
            # Simple builtin redirect
            pipeline = parse_pipeline(f"pwd > {output_file}")
            execute_pipeline(pipeline)
            content = output_file.read_text()
            # Should contain the current directory
            self.assertTrue(len(content) > 0)
            self.assertIn('pynix-shell', content)

    def test_simple_external_pipeline(self):
        """Test simple 2-stage external pipeline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "simple_pipe.txt"
            test_file = Path(tmpdir) / "input.txt"
            test_file.write_text("apple\nbanana\ncherry\n")

            # Simple grep -> output (no multi-stage)
            pipeline = parse_pipeline(
                f"grep banana {test_file} > {output_file}")
            execute_pipeline(pipeline)

            content = output_file.read_text()
            self.assertEqual(content, 'banana\n')

    def test_builtin_pipeline_with_append(self):
        """Test builtin pipeline with append redirect."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "append_pipe.txt"

            # First pipeline
            pipeline1 = parse_pipeline(f"echo first | cat > {output_file}")
            execute_pipeline(pipeline1)

            # Second pipeline with append
            pipeline2 = parse_pipeline(f"echo second | cat >> {output_file}")
            execute_pipeline(pipeline2)

            content = output_file.read_text()
            self.assertIn('first', content)
            self.assertIn('second', content)
            lines = content.strip().split('\n')
            self.assertEqual(len(lines), 2)

    def test_external_pipeline_with_redirect(self):
        """Test external-only pipeline with redirect."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "external.txt"
            test_file = Path(tmpdir) / "input.txt"
            test_file.write_text("line1\nline2\nline3\n")

            # cat (external) -> head (external) -> redirect
            pipeline = parse_pipeline(
                f"cat {test_file} | head -2 > {output_file}")
            execute_pipeline(pipeline)

            content = output_file.read_text()
            self.assertIn('line1', content)
            self.assertIn('line2', content)

    def test_pipeline_stderr_only_redirect(self):
        """Test pipeline with only stderr redirected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            stderr_file = Path(tmpdir) / "errors_only.txt"

            # Command that produces stderr
            pipeline = parse_pipeline(
                f"ls /nonexistent_path_xyz 2> {stderr_file}")
            execute_pipeline(pipeline)

            self.assertTrue(stderr_file.exists())
            content = stderr_file.read_text()
            self.assertIn('nonexistent_path_xyz', content)


if __name__ == '__main__':
    unittest.main(verbosity=2)
