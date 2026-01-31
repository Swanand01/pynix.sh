from app.parsing import parse_pipeline
from app.parsing.pipeline import execute_pipeline_captured
from app.core.external import execute_external
import unittest
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestSubprocessCapture(unittest.TestCase):
    """Test subprocess output capture for $() and !() operators."""

    def test_capture_simple_command(self):
        """Test capturing output from a simple command."""
        segment = {'parts': ['echo', 'hello'],
                   'stdout_redirs': [], 'stderr_redirs': []}
        result = execute_external(segment, capture=True)
        self.assertIsNotNone(result)
        returncode, stdout, stderr = result
        self.assertEqual(returncode, 0)
        self.assertEqual(stdout, 'hello\n')
        self.assertEqual(stderr, '')

    def test_capture_command_not_found(self):
        """Test capturing when command doesn't exist."""
        segment = {'parts': ['nonexistent_cmd_xyz'],
                   'stdout_redirs': [], 'stderr_redirs': []}
        result = execute_external(segment, capture=True)
        self.assertIsNone(result)

    def test_capture_command_with_args(self):
        """Test capturing command with arguments."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.txt"
            test_file.write_text("apple\nbanana\ncherry\n")
            segment = {'parts': ['grep', 'banana', str(test_file)], 'stdout_redirs': [
            ], 'stderr_redirs': []}
            result = execute_external(segment, capture=True)
            self.assertIsNotNone(result)
            returncode, stdout, stderr = result
            self.assertEqual(returncode, 0)
            self.assertEqual(stdout, 'banana\n')

    def test_capture_command_with_error(self):
        """Test capturing command that produces stderr."""
        segment = {'parts': ['ls', '/nonexistent_dir_xyz'],
                   'stdout_redirs': [], 'stderr_redirs': []}
        result = execute_external(segment, capture=True)
        self.assertIsNotNone(result)
        returncode, stdout, stderr = result
        self.assertNotEqual(returncode, 0)
        self.assertIn('nonexistent_dir_xyz', stderr)

    def test_capture_pipeline_simple(self):
        """Test capturing pipeline output."""
        pipeline = parse_pipeline("echo hello | grep h")
        returncode, stdout, stderr = execute_pipeline_captured(pipeline)
        self.assertEqual(returncode, 0)
        self.assertEqual(stdout, 'hello\n')

    def test_capture_pipeline_no_match(self):
        """Test capturing pipeline with no output."""
        pipeline = parse_pipeline("echo hello | grep xyz")
        returncode, stdout, stderr = execute_pipeline_captured(pipeline)
        self.assertEqual(returncode, 1)  # grep returns 1 when no match
        self.assertEqual(stdout, '')

    def test_capture_pipeline_multi_stage(self):
        """Test capturing multi-stage pipeline."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "data.txt"
            test_file.write_text("line1\nline2\nline3\n")
            pipeline = parse_pipeline(f"cat {test_file} | grep line | head -2")
            returncode, stdout, stderr = execute_pipeline_captured(pipeline)
            self.assertEqual(returncode, 0)
            lines = stdout.strip().split('\n')
            self.assertEqual(len(lines), 2)
            self.assertIn('line1', stdout)
            self.assertIn('line2', stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
