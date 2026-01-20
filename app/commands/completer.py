import readline
import platform


def create_completer(options):
    sorted_options = sorted(options)

    def completer(text, state):
        # Build list of all matches for the current text
        if text:
            matches = [
                opt + " " for opt in sorted_options if opt.startswith(text)]
        else:
            matches = sorted_options

        # Return the match at index 'state', or None if no more
        return matches[state] if state < len(matches) else None

    return completer


def setup_completion(builtin_commands=[]):
    completer = create_completer(builtin_commands)
    readline.set_completer(completer)

    if platform.system() == 'Darwin':
        readline.parse_and_bind('bind ^I rl_complete')
    else:
        readline.parse_and_bind('tab: complete')
