import readline
import platform
from ..utils import get_executable_completions


def create_completer(builtins):
    """Create a completer that completes both builtins and PATH executables."""

    def completer(text, state):
        # On first call (state=0), build the match list
        if state == 0:
            # Start with builtin matches
            matches = [cmd for cmd in builtins if cmd.startswith(text)]

            # Add PATH executable matches
            path_matches = get_executable_completions(text)
            matches.extend(path_matches)

            # Remove duplicates and sort once
            matches = sorted(set(matches))

            # Add space after each match for convenience
            completer.matches = [m + " " for m in matches]

        # Return the match at index 'state', or None if no more
        return completer.matches[state] if state < len(completer.matches) else None

    completer.matches = []
    return completer


def setup_completion(builtin_commands=[]):
    completer = create_completer(builtin_commands)
    readline.set_completer(completer)

    if platform.system() == 'Darwin':
        readline.parse_and_bind('bind ^I rl_complete')
    else:
        readline.parse_and_bind('tab: complete')
