import os


def file_exists_in_path(filename):
    """Check if a file exists in any directory in PATH and is executable."""
    path = os.environ['PATH']
    directories = path.split(os.pathsep)
    for directory in directories:
        file_path = os.path.join(directory, filename)
        if os.path.isfile(file_path) and os.access(file_path, os.X_OK):
            return True, file_path
    return False, None
