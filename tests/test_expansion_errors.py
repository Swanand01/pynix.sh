import unittest
import tempfile
import os
from app.core.shell.expansions import shell, expand_nested_substitutions


class TestExpansionErrors(unittest.TestCase):
    """Test that expansion errors are handled cleanly."""

    def setUp(self):
        """Set up test environment."""
        # Use temp directory to avoid polluting workspace
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

    def tearDown(self):
        """Clean up temp directory."""
        os.chdir(self.original_cwd)
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_undefined_variable_in_at_expansion(self):
        """Test that undefined variables in @() raise RuntimeError, not create files."""
        # Should raise RuntimeError about the undefined variable
        with self.assertRaises(RuntimeError) as context:
            shell("touch @(undefined_var)", capture='stdout')

        # Error message should mention the variable
        self.assertIn("undefined_var", str(context.exception))
        self.assertIn("@(", str(context.exception))

        # Most importantly: no files with "<error:" in the name should be created
        files = os.listdir(self.temp_dir)
        error_files = [f for f in files if '<error' in f or 'error:' in f]
        self.assertEqual([], error_files,
                         f"Error text should not create files, but found: {error_files}")

    def test_syntax_error_in_at_expansion(self):
        """Test that Python syntax errors in @() are caught properly."""
        with self.assertRaises(Exception):
            shell("echo @(1 +)", capture='stdout')

    def test_nested_expansion_error(self):
        """Test error in nested expansion like $(echo @(undefined))."""
        with self.assertRaises(RuntimeError) as context:
            shell("echo @(nonexistent)", capture='stdout')

        self.assertIn("nonexistent", str(context.exception))

    def test_successful_expansion_creates_file(self):
        """Verify that valid expansions still work correctly."""
        # Create a scope with the filename variable
        scope = {"filename": "test.txt"}

        # Use expand_nested_substitutions to expand with the scope
        expanded = expand_nested_substitutions("touch @(filename)", scope)
        self.assertEqual("touch test.txt", expanded)

        # Execute the expanded command
        shell(expanded, capture=None)

        # Should create test.txt, not error files
        files = os.listdir(self.temp_dir)
        self.assertIn("test.txt", files)

    def test_error_message_is_concise(self):
        """Test that error messages don't include verbose wrapper text."""
        with self.assertRaises(RuntimeError) as context:
            shell("echo @(undefined)", capture='stdout')

        error_msg = str(context.exception)
        # Should NOT contain "Error evaluating" wrapper
        self.assertNotIn("Error evaluating", error_msg)
        # Should be concise: @(undefined): name 'undefined' is not defined
        self.assertIn("@(undefined)", error_msg)
        self.assertIn("name 'undefined' is not defined", error_msg)


if __name__ == '__main__':
    unittest.main()
