"""Verify providers don't import rich.console at module level."""

import importlib
import sys

MODULES_TO_CHECK = [
    "par_cli_tts.providers.openai",
    "par_cli_tts.providers.deepgram",
    "par_cli_tts.providers.gemini",
    "par_cli_tts.voice_cache",
    "par_cli_tts.model_downloader",
    "par_cli_tts.errors",
]


def test_no_rich_console_import_in_providers():
    """Provider modules should not import from par_cli_tts.console."""
    for mod_name in MODULES_TO_CHECK:
        if mod_name in sys.modules:
            mod = sys.modules[mod_name]
        else:
            mod = importlib.import_module(mod_name)

        source = getattr(mod, "__file__", None)
        if source:
            with open(source) as f:
                content = f.read()
            assert "from par_cli_tts.console import" not in content, (
                f"{mod_name} still imports from par_cli_tts.console"
            )
