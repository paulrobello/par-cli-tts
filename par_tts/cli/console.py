"""Shared console instance for consistent output handling.

This module provides a single Console instance that can be imported
by all modules for consistent output formatting.
"""

from rich.console import Console

# Shared console instance for standard output
console = Console()

# Console instance for error output (writes to stderr)
error_console = Console(stderr=True)
