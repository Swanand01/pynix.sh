import subprocess
from ..utils import file_exists_in_path


def handle_external_command(cmd, args, stdout_spec=None, stderr_spec=None):
    """
    Execute an external command with optional stdout/stderr redirection.

    Args:
        cmd: Command name to execute
        args: List of arguments
        stdout_spec: None or tuple(path, mode) for stdout redirection
        stderr_spec: None or tuple(path, mode) for stderr redirection
    """
    file_exists, _ = file_exists_in_path(cmd)
    if not file_exists:
        print(f"{cmd}: command not found")
        return

    stdout_arg = open(stdout_spec[0], stdout_spec[1]) if stdout_spec else None
    stderr_arg = open(stderr_spec[0], stderr_spec[1]) if stderr_spec else None

    subprocess.run([cmd, *args], stdout=stdout_arg, stderr=stderr_arg)

    if stdout_arg:
        stdout_arg.close()
    if stderr_arg:
        stderr_arg.close()
