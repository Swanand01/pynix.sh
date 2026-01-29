from prompt_toolkit.completion import Completer, Completion
from ..utils import get_executable_completions


class ShellCompleter(Completer):
    """
    Simple xonsh-style completer.

    - At the first token it completes builtins and executables from $PATH.
    - For later tokens it currently reuses executable completion as a
      lightweight argument/path heuristic.
    """

    def __init__(self, builtins=None):
        # Builtin command names (exit, echo, pwd, cd, history, ...) if provided
        self.builtins = builtins or []

    def get_completions(self, document, complete_event):
        text_before = document.text_before_cursor
        word = document.get_word_before_cursor(WORD=True)

        if not word:
            return

        # Are we completing the first token on the line?
        stripped = text_before.lstrip()
        is_first_token = stripped.startswith(
            word) and " " not in stripped.split(word, 1)[0]

        matches = set()

        if is_first_token:
            # First token → shell command position
            matches.update(
                cmd for cmd in self.builtins if cmd.startswith(word))
            matches.update(get_executable_completions(word))
        else:
            # Later tokens → lightweight argument/path completion
            matches.update(get_executable_completions(word))

        for m in sorted(matches):
            yield Completion(m, start_position=-len(word))
