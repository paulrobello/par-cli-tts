"""Compatibility shim -- import from par_tts instead.

This module re-exports the public API from ``par_tts`` for backward
compatibility.  It will be removed in **v0.7.0** (two minor versions
after the rename in v0.5.0).  Do not add new exports here.
"""

import warnings

from par_tts import *  # noqa: F401,F403
from par_tts import __version__, get_provider, list_providers  # noqa: F401

warnings.warn(
    "Importing from 'par_cli_tts' is deprecated. Use 'import par_tts' instead. "
    "The par_cli_tts package will be removed in v0.7.0.",
    DeprecationWarning,
    stacklevel=2,
)
