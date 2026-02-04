"""Core execution engine for the unified shell."""

from .orchestration.runner import run_command
from .python.execution import execute_python
from .python.namespace import get_namespace, initialize_namespace
from .shell.execution import execute_external, execute_shell
from .shell.pipeline import execute_pipeline, execute_pipeline_captured
from .shell.expansions import expand_at, shell
from ..types import CommandResult

# Initialize namespace with runtime functions
initialize_namespace(expand_at, shell)

__all__ = [
    'execute_python',
    'get_namespace',
    'initialize_namespace',
    'execute_external',
    'execute_shell',
    'run_command',
    'execute_pipeline',
    'execute_pipeline_captured',
    'shell',
    'expand_at',
    'execute_bang',
    'CommandResult',
]
