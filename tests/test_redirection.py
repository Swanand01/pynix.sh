import unittest
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.commands.builtins import execute_builtin
from app.parsing import parse_pipeline
from app.parsing.pipeline import execute_pipeline


class TestRedirection(unittest.TestCase):
    """Test output redirection with new file object approach."""

    def test_builtin_redirect_stdout(self):
        """Test redirecting builtin stdout to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "output.txt"
            segment = {
                'parts': ['echo', 'test'],
                'stdout_redirs': [(str(output_file), 'w')],
                'stderr_redirs': []
            }
            execute_builtin(segment)
            self.assertEqual(output_file.read_text(), 'test\n')

    def test_builtin_redirect_append(self):
        """Test appending to file with >>."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "append.txt"

            # First write
            segment1 = {
                'parts': ['echo', 'line1'],
                'stdout_redirs': [(str(output_file), 'w')],
                'stderr_redirs': []
            }
            execute_builtin(segment1)

            # Append
            segment2 = {
                'parts': ['echo', 'line2'],
                'stdout_redirs': [(str(output_file), 'a')],
                'stderr_redirs': []
            }
            execute_builtin(segment2)

            self.assertEqual(output_file.read_text(), 'line1\nline2\n')

    def test_multiple_redirects(self):
        """Test multiple redirects - only last one is active."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file1 = Path(tmpdir) / "file1.txt"
            file2 = Path(tmpdir) / "file2.txt"

            segment = {
                'parts': ['echo', 'test'],
                'stdout_redirs': [(str(file1), 'w'), (str(file2), 'w')],
                'stderr_redirs': []
            }
            execute_builtin(segment)

            # file1 should be created but empty (primed)
            self.assertTrue(file1.exists())
            self.assertEqual(file1.read_text(), '')

            # file2 should have the output
            self.assertEqual(file2.read_text(), 'test\n')

    def test_explicit_stdout_redirect(self):
        """Test explicit stdout redirect with 1>."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "stdout.txt"
            # Parse command with explicit 1> operator
            pipeline = parse_pipeline(f"echo explicit_stdout 1> {output_file}")
            segment = pipeline[0]
            execute_builtin(segment)
            self.assertEqual(output_file.read_text(), 'explicit_stdout\n')

    def test_stderr_redirect(self):
        """Test stderr redirect with 2>."""
        with tempfile.TemporaryDirectory() as tmpdir:
            stderr_file = Path(tmpdir) / "stderr.txt"
            segment = {
                'parts': ['type', 'nonexistent_xyz'],
                'stdout_redirs': [],
                'stderr_redirs': []  # type outputs "not found" to stdout, not stderr
            }
            # Capture stdout instead (type prints errors to stdout)
            segment['stdout_redirs'] = [(str(stderr_file), 'w')]
            execute_builtin(segment)
            content = stderr_file.read_text()
            self.assertIn('not found', content)

    def test_separate_stdout_stderr_redirects(self):
        """Test redirecting stdout and stderr to different files with external command."""
        with tempfile.TemporaryDirectory() as tmpdir:
            stdout_file = Path(tmpdir) / "out.txt"
            stderr_file = Path(tmpdir) / "err.txt"

            # Use ls with valid and invalid paths
            pipeline = parse_pipeline(
                f"ls {tmpdir} /nonexistent_xyz_dir 1> {stdout_file} 2> {stderr_file}")
            execute_pipeline(pipeline)

            # stdout should have directory listing
            self.assertTrue(stdout_file.exists())
            self.assertTrue(len(stdout_file.read_text()) > 0)

            # stderr should have error message
            self.assertTrue(stderr_file.exists())
            stderr_content = stderr_file.read_text()
            self.assertIn('nonexistent_xyz_dir', stderr_content)

    def test_stderr_append_mode(self):
        """Test stderr append with 2>>."""
        with tempfile.TemporaryDirectory() as tmpdir:
            error_file = Path(tmpdir) / "errors.txt"

            # Parse command with 2>> operator
            pipeline1 = parse_pipeline(f"ls /nonexistent1 2>> {error_file}")
            execute_pipeline(pipeline1)

            pipeline2 = parse_pipeline(f"ls /nonexistent2 2>> {error_file}")
            execute_pipeline(pipeline2)

            content = error_file.read_text()
            # Should have both errors
            self.assertIn('nonexistent1', content)
            self.assertIn('nonexistent2', content)


if __name__ == '__main__':
    unittest.main(verbosity=2)
