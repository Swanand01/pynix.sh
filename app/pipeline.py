import sys
import os
from .redirection import prepare_redirects
from .commands import run_builtin, Command


def redirect_io_for_pipeline(i, n, pipes, stdout_spec, stderr_spec):
    """
    Setup stdin/stdout/stderr for command at position i in pipeline.

    Args:
        i: Position in pipeline (0=first, 1=second, etc.)
        n: Total number of commands
        pipes: List of (read_fd, write_fd) tuples
        stdout_spec: (filename, mode) for stdout redirect, or None
        stderr_spec: (filename, mode) for stderr redirect, or None
    """
    is_first = (i == 0)
    is_last = (i == n - 1)

    # STDIN: Where does this command read from?
    if not is_first:
        # Middle/last command: read from previous command's output
        os.dup2(pipes[i-1][0], 0)  # stdin ← previous pipe
    # (first command: stdin stays as terminal)

    # STDOUT: Where does this command write to?
    if not is_last:
        # First/middle command: write to next command
        os.dup2(pipes[i][1], 1)  # stdout → next pipe
    elif stdout_spec:
        # Last command with > or >>: write to file
        fd = os.open(stdout_spec[0],
                     os.O_WRONLY | os.O_CREAT |
                     (os.O_APPEND if stdout_spec[1] == 'a' else os.O_TRUNC),
                     0o644)
        os.dup2(fd, 1)  # stdout → file
        os.close(fd)
    # (last command without redirect: stdout stays as terminal)

    # STDERR: Error output (only redirect on last command)
    if is_last and stderr_spec:
        fd = os.open(stderr_spec[0],
                     os.O_WRONLY | os.O_CREAT |
                     (os.O_APPEND if stderr_spec[1] == 'a' else os.O_TRUNC),
                     0o644)
        os.dup2(fd, 2)  # stderr → file
        os.close(fd)


def execute_pipeline(pipeline):
    """
    Execute commands connected by pipes.

    How it works:
    1. Create pipes to connect commands
    2. Fork a child process for each command
    3. Each child: redirects its I/O, then runs the command
    4. Parent: waits for all children to finish

    Example: ls | grep py | wc -l

        ls ----[pipe0]----> grep ----[pipe1]----> wc
                                                    |
                                                terminal
    """
    if not pipeline:
        return

    # Reject cd and exit in pipelines (they need to affect parent shell)
    if len(pipeline) > 1:
        for segment in pipeline:
            cmd = segment['parts'][0] if segment['parts'] else None
            if cmd in [Command.CD, Command.EXIT]:
                print(f"{cmd}: cannot be used in pipeline", file=sys.stderr)
                return

    n = len(pipeline)

    # STEP 1: Create pipes
    # For n commands, we need n-1 pipes
    # Example: 3 commands need 2 pipes
    #   cmd0 → pipe0 → cmd1 → pipe1 → cmd2
    pipes = []
    for i in range(n - 1):
        read_fd, write_fd = os.pipe()
        pipes.append((read_fd, write_fd))

    # STEP 2: Fork and execute each command
    pids = []

    for i, segment in enumerate(pipeline):
        cmd_parts = segment['parts']
        if not cmd_parts:
            continue

        cmd = cmd_parts[0]
        args = cmd_parts[1:]
        is_builtin = is_builtin(cmd)

        # Get file redirects (>, >>, 2>, 2>>)
        stdout_spec, stderr_spec = prepare_redirects(
            segment['stdout_redirs'],
            segment['stderr_redirs']
        )

        # Fork: create a child process for this command
        pid = os.fork()

        if pid == 0:  # CHILD PROCESS
            # 1. Redirect stdin/stdout/stderr
            redirect_io_for_pipeline(i, n, pipes, stdout_spec, stderr_spec)

            # 2. Close all pipe file descriptors
            # (We already dup2'd the ones we need, close originals to prevent hanging)
            for read_fd, write_fd in pipes:
                os.close(read_fd)
                os.close(write_fd)

            # 3. Run the command
            if is_builtin:
                # Builtin: run our Python function
                run_builtin(cmd, args)
                sys.exit(0)  # Must exit child process
            else:
                # External: replace this process with the command
                try:
                    os.execvp(cmd, [cmd] + args)
                except FileNotFoundError:
                    print(f"{cmd}: command not found", file=sys.stderr)
                    sys.exit(127)

        # PARENT PROCESS
        pids.append(pid)  # Remember child's PID

    # STEP 3: Parent closes all pipes
    # (Children have their own copies, parent must close to prevent hanging)
    for read_fd, write_fd in pipes:
        os.close(read_fd)
        os.close(write_fd)

    # STEP 4: Wait for all children to finish
    for pid in pids:
        os.waitpid(pid, 0)
