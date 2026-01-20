import os


def get_path_directories():
    """Get list of directories from PATH environment variable."""
    return os.environ['PATH'].split(os.pathsep)


def is_executable(file_path):
    """Check if a file path is an executable file."""
    return os.path.isfile(file_path) and os.access(file_path, os.X_OK)


def executable_exists_in_path(filename):
    """Check if a file exists in any directory in PATH and is executable."""
    for directory in get_path_directories():
        file_path = os.path.join(directory, filename)
        if is_executable(file_path):
            return True, file_path
    return False, None


def get_executable_completions(prefix):
    """Get all executables in PATH that start with the given prefix."""
    matches = set()

    for directory in get_path_directories():
        try:
            filenames = os.listdir(directory)
        except (OSError, PermissionError):
            continue

        # Check each file
        for filename in filenames:
            if not filename.startswith(prefix):
                continue

            file_path = os.path.join(directory, filename)
            if is_executable(file_path):
                matches.add(filename)

    return matches
