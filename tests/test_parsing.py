import unittest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.parsing import parse_pipeline


class TestCommandParsing(unittest.TestCase):
    """Test command parsing and pipeline parsing."""

    def test_parse_simple_command(self):
        """Test parsing a simple command."""
        pipeline = parse_pipeline("echo hello")
        self.assertEqual(len(pipeline), 1)
        self.assertEqual(pipeline[0]['parts'], ['echo', 'hello'])
        self.assertEqual(pipeline[0]['stdout_redirs'], [])

    def test_parse_command_with_redirect(self):
        """Test parsing command with redirection."""
        pipeline = parse_pipeline("echo test > file.txt")
        self.assertEqual(len(pipeline), 1)
        self.assertEqual(pipeline[0]['parts'], ['echo', 'test'])
        self.assertEqual(len(pipeline[0]['stdout_redirs']), 1)
        self.assertEqual(pipeline[0]['stdout_redirs'][0], ('file.txt', 'w'))

    def test_parse_pipeline(self):
        """Test parsing multi-command pipeline."""
        pipeline = parse_pipeline("ls | grep py | wc")
        self.assertEqual(len(pipeline), 3)
        self.assertEqual(pipeline[0]['parts'], ['ls'])
        self.assertEqual(pipeline[1]['parts'], ['grep', 'py'])
        self.assertEqual(pipeline[2]['parts'], ['wc'])

    def test_parse_append_redirect(self):
        """Test parsing append redirect."""
        pipeline = parse_pipeline("echo test >> file.txt")
        self.assertEqual(pipeline[0]['stdout_redirs'][0], ('file.txt', 'a'))

    def test_parse_stderr_redirect(self):
        """Test parsing stderr redirect."""
        pipeline = parse_pipeline("ls 2> errors.txt")
        self.assertEqual(len(pipeline[0]['stderr_redirs']), 1)
        self.assertEqual(pipeline[0]['stderr_redirs'][0], ('errors.txt', 'w'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
