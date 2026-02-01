import sys
import os
import shlex
import subprocess
import threading
from ..parsing import prepare_redirects, expand_path
from ..types import Command, is_builtin
from ..commands import execute_builtin


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

    # Join pipeline segments back into shell command
    commands = []
    for segment in pipeline:
        cmd_str = ' '.join(shlex.quote(part) for part in segment['parts'])
        if cmd_str:
            commands.append(cmd_str)

    if not commands:
        return (0, '', '')

    full_command = ' | '.join(commands)
    result = subprocess.run(
        full_command,
        shell=True,
        capture_output=True,
        text=True
    )
    return (result.returncode, result.stdout, result.stderr)


def execute_pipeline(pipeline):
    """
    Execute commands connected by pipes (cross-platform version).

    Uses subprocess.Popen for external commands and threads for builtins.
    This approach works on Windows, macOS, and Linux.

    Example: echo hello | grep h | wc -l
        echo ---[pipe0]---> grep ---[pipe1]---> wc
    """
    if not pipeline:
        return

    # Reject cd and exit in pipelines (they need to affect parent shell)
    if len(pipeline) > 1:
        for segment in pipeline:
            cmd = segment['parts'][0] if segment['parts'] else None
            if cmd in (Command.CD, Command.EXIT):
                print(f"{cmd}: cannot be used in pipeline", file=sys.stderr)
                return

    n = len(pipeline)
    processes = []
    threads = []
    pipe_fds = []  # Track which fds we still own
    redirect_files = []  # Track file objects we opened for cleanup

    # STEP 1: Create pipes
    # For n commands, we need n-1 pipes
    pipes = []
    for i in range(n - 1):
        r, w = os.pipe()
        pipes.append((r, w))
        pipe_fds.extend([r, w])

    # STEP 2: Execute each command
    for i, segment in enumerate(pipeline):
        cmd_parts = segment['parts']
        if not cmd_parts:
            continue

        cmd = cmd_parts[0]
        args = [expand_path(arg) for arg in cmd_parts[1:]]

        # Get file redirects (>, >>, 2>, 2>>)
        stdout_spec, stderr_spec = prepare_redirects(
            segment['stdout_redirs'],
            segment['stderr_redirs']
        )

        # Determine stdin source
        if i == 0:
            stdin_arg = None  # First command reads from terminal
        else:
            stdin_arg = pipes[i-1][0]  # Read from previous pipe

        # Determine stdout destination
        if i == n - 1:
            # Last command
            if stdout_spec:
                stdout_arg = open(stdout_spec[0], stdout_spec[1])
                redirect_files.append(stdout_arg)  # Track for cleanup
            else:
                stdout_arg = None  # Write to terminal
        else:
            # Not last command - write to next pipe
            stdout_arg = pipes[i][1]

        # Determine stderr destination (only for last command)
        if i == n - 1 and stderr_spec:
            stderr_arg = open(stderr_spec[0], stderr_spec[1])
            redirect_files.append(stderr_arg)  # Track for cleanup
        else:
            stderr_arg = None

        # Execute the command
        if is_builtin(cmd):
            # Builtin: run in a thread with file objects
            # Convert stdin fd to file object (for reading)
            if stdin_arg is not None:
                stdin_file = os.fdopen(stdin_arg, 'r')
                pipe_fds.remove(stdin_arg)  # os.fdopen takes ownership
            else:
                stdin_file = None

            # Convert stdout fd to file object (for writing)
            if isinstance(stdout_arg, int):
                stdout_file = os.fdopen(stdout_arg, 'w')
                pipe_fds.remove(stdout_arg)  # os.fdopen takes ownership
            else:
                stdout_file = stdout_arg

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
            threads.append((thread, result_holder))
        else:
            # External command: use subprocess.Popen
            try:
                proc = subprocess.Popen(
                    [cmd] + args,
                    stdin=stdin_arg,
                    stdout=stdout_arg,
                    stderr=stderr_arg
                )
                processes.append(proc)

                # IMPORTANT: Close parent's copies of pipe fds
                # subprocess.Popen creates copies for the child, parent must close its copies
                if isinstance(stdin_arg, int) and stdin_arg in pipe_fds:
                    os.close(stdin_arg)
                    pipe_fds.remove(stdin_arg)
                if isinstance(stdout_arg, int) and stdout_arg in pipe_fds:
                    os.close(stdout_arg)
                    pipe_fds.remove(stdout_arg)

            except FileNotFoundError:
                print(f"{cmd}: command not found", file=sys.stderr)

    # STEP 3: Close all remaining pipe file descriptors in parent
    # (Ones that were passed to subprocess or os.fdopen are already removed)
    for fd in pipe_fds:
        try:
            os.close(fd)
        except OSError:
            pass

    # STEP 4: Wait for all threads first (they need to finish writing before processes can finish reading)
    for thread, result_holder in threads:
        thread.join()

    # STEP 5: Wait for all processes
    for proc in processes:
        proc.wait()

    # STEP 6: Close any redirect files we opened
    for f in redirect_files:
        try:
            f.close()
        except OSError:
            pass
