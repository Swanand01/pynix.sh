from prompt_toolkit.completion import Completer, Completion, PathCompleter, ExecutableCompleter
from prompt_toolkit.document import Document


class ShellCompleter(Completer):
    """
    Shell completer with command and path completion.

    - First token: builtins and executables from $PATH
    - Other tokens: file/folder paths via PathCompleter
    """

    def __init__(self, builtins=None):
        self.builtins = builtins or []
        self.path_completer = PathCompleter(expanduser=True)
        self.executable_completer = ExecutableCompleter()

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        seen = set()

        # Extract the current word (after last space, or whole text)
        if ' ' in text:
            word_start = text.rfind(' ') + 1
            is_first_token = False
        else:
            word_start = 0
            is_first_token = True

        word = text[word_start:]
        sub_doc = Document(word)

        # Path completions (always available)
        for completion in self.path_completer.get_completions(sub_doc, complete_event):
            full_path = word[:len(
                word) + completion.start_position] + completion.text

            if full_path not in seen:
                seen.add(full_path)
                yield Completion(
                    completion.text,
                    start_position=completion.start_position,
                    display=completion.display,
                )

        # Command completions (first token only)
        if is_first_token and word:
            for cmd in self.builtins:
                if cmd.startswith(word) and cmd not in seen:
                    seen.add(cmd)
                    yield Completion(cmd, start_position=-len(word))

            for completion in self.executable_completer.get_completions(sub_doc, complete_event):
                # Calculate full command name (word prefix + completion suffix)
                full_cmd = word[:len(
                    word) + completion.start_position] + completion.text

                if full_cmd not in seen:
                    seen.add(full_cmd)
                    yield Completion(
                        completion.text,
                        start_position=completion.start_position,
                        display=completion.display,
                    )
