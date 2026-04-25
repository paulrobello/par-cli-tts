"""Verify par_tts library modules don't import rich.console at module level."""

import importlib
import sys

MODULES_TO_CHECK = [
    "par_tts.providers.openai",
    "par_tts.providers.deepgram",
    "par_tts.providers.gemini",
    "par_tts.providers.elevenlabs",
    "par_tts.voice_cache",
    "par_tts.model_downloader",
    "par_tts.errors",
]


def test_no_rich_console_import_in_library():
    """Library modules should not import from any console module."""
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
            assert "from par_tts.cli.console import" not in content, (
                f"{mod_name} imports from CLI console (not library-safe)"
            )
