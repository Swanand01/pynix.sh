import unittest
import os
import sys
from io import StringIO

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.parsing import parse_pipeline
from app.parsing.pipeline import execute_pipeline


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def test_empty_command(self):
        """Test handling empty command."""
        pipeline = parse_pipeline("")
        self.assertEqual(len(pipeline), 1)
        self.assertEqual(pipeline[0]['parts'], [])

    def test_cd_in_pipeline_rejected(self):
        """Test that cd in pipeline is rejected."""
        old_stderr = sys.stderr
        sys.stderr = StringIO()
        try:
            pipeline = parse_pipeline("echo test | cd /tmp")
            execute_pipeline(pipeline)
            output = sys.stderr.getvalue()
            self.assertIn('cannot be used in pipeline', output)
        finally:
            sys.stderr = old_stderr

    def test_exit_in_pipeline_rejected(self):
        """Test that exit in pipeline is rejected."""
        old_stderr = sys.stderr
        sys.stderr = StringIO()
        try:
            pipeline = parse_pipeline("echo test | exit")
            execute_pipeline(pipeline)
            output = sys.stderr.getvalue()
            self.assertIn('cannot be used in pipeline', output)
        finally:
            sys.stderr = old_stderr


if __name__ == '__main__':
    unittest.main(verbosity=2)
