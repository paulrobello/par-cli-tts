"""Compatibility shim — import from par_tts instead.

This module re-exports the public API from ``par_tts`` for backward
compatibility.  It will be removed in a future release.
"""

import warnings

from par_tts import *  # noqa: F401,F403
from par_tts import __version__, get_provider, list_providers  # noqa: F401

warnings.warn(
    "Importing from 'par_cli_tts' is deprecated. Use 'import par_tts' instead.",
    DeprecationWarning,
    stacklevel=2,
)
