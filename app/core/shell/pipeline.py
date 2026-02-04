import sys
import os
import shlex
import subprocess
import threading
from ...parsing import prepare_redirect_specs, expand_path
from ...types import Command, is_builtin
from ...commands import execute_builtin


def build_shell_command(pipeline):
    """Build a shell command string from pipeline segments."""
    commands = []
    for segment in pipeline:
        cmd_str = ' '.join(shlex.quote(part) for part in segment['parts'])
        if cmd_str:
            commands.append(cmd_str)
    return ' | '.join(commands) if commands else ''


def execute_pipeline_captured(pipeline):
    """
    Execute a pipeline and capture final output.

    Args:
        pipeline: List of pipeline segments

    Returns:
        (returncode, stdout, stderr) tuple with captured output as strings
    """
    if not pipeline:
        return (0, '', '')

    full_command = build_shell_command(pipeline)
    if not full_command:
        return (0, '', '')

    result = subprocess.run(
        full_command,
        shell=True,
        capture_output=True,
        text=True
    )
    return (result.returncode, result.stdout, result.stderr)


def validate_pipeline_commands(pipeline):
    """Validate that cd and exit aren't used in multi-command pipelines."""
    if len(pipeline) <= 1:
        return True

    for segment in pipeline:
        cmd = segment['parts'][0] if segment['parts'] else None
        if cmd in (Command.CD, Command.EXIT):
            print(f"{cmd}: cannot be used in pipeline", file=sys.stderr)
            return False
    return True


def create_pipeline_pipes(n_commands):
    """Create n-1 pipes for n commands in a pipeline."""
    pipes = []
    pipe_fds = []

    for _ in range(n_commands - 1):
        r, w = os.pipe()
        pipes.append((r, w))
        pipe_fds.extend([r, w])

    return pipes, pipe_fds


def get_stdin_for_command(i, pipes):
    """Get stdin file descriptor/arg for command at position i."""
    if i == 0:
        return None  # First command reads from terminal
    return pipes[i-1][0]  # Read from previous pipe


def get_stdout_for_command(i, n_commands, pipes, stdout_spec, redirect_files):
    """Get stdout file descriptor/arg for command at position i."""
    if i == n_commands - 1:
        # Last command
        if stdout_spec:
            stdout_arg = open(stdout_spec[0], stdout_spec[1])
            redirect_files.append(stdout_arg)
            return stdout_arg
        return None  # Write to terminal

    # Not last command - write to next pipe
    return pipes[i][1]


def get_stderr_for_command(i, n_commands, stderr_spec, redirect_files):
    """Get stderr file descriptor/arg for last command in pipeline."""
    # Last command
    if i == n_commands - 1 and stderr_spec:
        stderr_arg = open(stderr_spec[0], stderr_spec[1])
        redirect_files.append(stderr_arg)
        return stderr_arg

    return None


def fd_to_file_object(fd, mode, pipe_fds):
    """Convert file descriptor to file object, removing from pipe_fds tracking."""
    if fd is None:
        return None
    if isinstance(fd, int):
        file_obj = os.fdopen(fd, mode)
        if fd in pipe_fds:
            pipe_fds.remove(fd)  # os.fdopen takes ownership
        return file_obj
    return fd  # Already a file object


def execute_builtin_in_pipeline(cmd, args, stdin_arg, stdout_arg, stderr_arg, pipe_fds):
    """Execute a builtin command in the pipeline using a thread."""
    # Convert fds to file objects
    stdin_file = fd_to_file_object(stdin_arg, 'r', pipe_fds)
    stdout_file = fd_to_file_object(stdout_arg, 'w', pipe_fds)
    stderr_file = stderr_arg

    result_holder = {'returncode': 0}
    thread = threading.Thread(
        target=execute_builtin,
        kwargs={
            'cmd': cmd,
            'args': args,
            'stdout': stdout_file,
            'stderr': stderr_file,
            'close_stdout': True,
            'result_holder': result_holder,
        }
    )
    thread.start()
    return (thread, result_holder)


def close_parent_pipe_fds(stdin_arg, stdout_arg, pipe_fds):
    """Close parent's copies of pipe fds after subprocess.Popen."""
    for fd in [stdin_arg, stdout_arg]:
        if isinstance(fd, int) and fd in pipe_fds:
            os.close(fd)
            pipe_fds.remove(fd)


def execute_external_in_pipeline(cmd, args, stdin_arg, stdout_arg, stderr_arg, pipe_fds):
    """Execute an external command in the pipeline using subprocess.Popen."""
    try:
        proc = subprocess.Popen(
            [cmd] + args,
            stdin=stdin_arg,
            stdout=stdout_arg,
            stderr=stderr_arg
        )
        # Close parent's copies of pipe fds (subprocess creates its own copies)
        close_parent_pipe_fds(stdin_arg, stdout_arg, pipe_fds)
        return proc
    except FileNotFoundError:
        print(f"{cmd}: command not found", file=sys.stderr)
        return None


def close_remaining_pipe_fds(pipe_fds):
    """Close all remaining pipe file descriptors in parent."""
    for fd in pipe_fds:
        try:
            os.close(fd)
        except OSError:
            pass


def close_redirect_files(redirect_files):
    """Close all opened redirect file objects."""
    for f in redirect_files:
        try:
            f.close()
        except OSError:
            pass


def wait_for_all_threads(threads):
    """Wait for all builtin threads to complete."""
    for thread, _ in threads:
        thread.join()


def wait_for_all_processes(processes):
    """Wait for all external processes to complete."""
    for proc in processes:
        proc.wait()


def get_pipeline_returncode(processes, threads):
    """Get the return code of the last command in the pipeline."""
    if processes:
        return processes[-1].returncode
    if threads:
        return threads[-1][1]['returncode']  # result_holder
    return 0


def execute_pipeline(pipeline):
    """
    Execute commands connected by pipes (cross-platform version).

    Uses subprocess.Popen for external commands and threads for builtins.
    This approach works on Windows, macOS, and Linux.

    Example: echo hello | grep h | wc -l
        echo ---[pipe0]---> grep ---[pipe1]---> wc

    Returns:
        returncode of the last command in the pipeline
    """
    if not pipeline:
        return 0

    # Validate commands in pipeline
    if not validate_pipeline_commands(pipeline):
        return 1

    n = len(pipeline)
    processes = []
    threads = []
    redirect_files = []

    # Create pipes for the pipeline
    pipes, pipe_fds = create_pipeline_pipes(n)

    # Execute each command in the pipeline
    for i, segment in enumerate(pipeline):
        cmd_parts = segment['parts']
        if not cmd_parts:
            continue

        cmd = cmd_parts[0]
        args = [expand_path(arg) for arg in cmd_parts[1:]]

        # Get file redirects (>, >>, 2>, 2>>)
        stdout_spec, stderr_spec = prepare_redirect_specs(
            segment['stdout_redirs'],
            segment['stderr_redirs']
        )

        # Determine I/O for this command
        stdin_arg = get_stdin_for_command(i, pipes)
        stdout_arg = get_stdout_for_command(
            i, n, pipes, stdout_spec, redirect_files)
        stderr_arg = get_stderr_for_command(i, n, stderr_spec, redirect_files)

        # Execute the command (builtin or external)
        if is_builtin(cmd):
            thread_result = execute_builtin_in_pipeline(
                cmd, args, stdin_arg, stdout_arg, stderr_arg, pipe_fds
            )
            threads.append(thread_result)
        else:
            proc = execute_external_in_pipeline(
                cmd, args, stdin_arg, stdout_arg, stderr_arg, pipe_fds
            )
            if proc:
                processes.append(proc)

    # Cleanup and wait for completion
    close_remaining_pipe_fds(pipe_fds)
    wait_for_all_threads(threads)
    wait_for_all_processes(processes)
    close_redirect_files(redirect_files)

    return get_pipeline_returncode(processes, threads)
