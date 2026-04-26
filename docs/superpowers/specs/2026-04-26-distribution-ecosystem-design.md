# Distribution & Ecosystem Design

## Scope

Implement the remaining `ideas.md` Distribution & Ecosystem items in-repo:

1. First-class shell completion helpers for bash, zsh, and fish.
2. Packaged voice-pack metadata for curated voice recommendations by use case.

The implementation will update project documentation and remove completed items from `ideas.md`.

## Shell Completion Helpers

`par-tts` will keep its existing single-command Typer interface and add discoverable helper flags:

- `--completion SHELL` prints a completion script for `bash`, `zsh`, or `fish`.
- `--completion-install SHELL` prints copy/paste installer instructions for the selected shell.

The script generation will use Typer/Click's standard completion environment variables, so behavior stays aligned with the CLI parser instead of maintaining custom shell completions by hand. Invalid shell names will fail with a user-facing `TTSError` categorized as invalid input.

## Voice-Pack Metadata

A small built-in catalog will ship with the package, stored as YAML under `par_tts/data/voice_packs.yaml`. Each pack will contain:

- `name`: stable pack identifier.
- `description`: human-readable use case.
- `voices`: ordered recommendations, each with `provider`, `voice`, optional `model`, and `notes`.

The CLI will add metadata-only flags:

- `--list-voice-packs` lists available packs and descriptions.
- `--show-voice-pack PACK` prints one pack's recommended voices.

These operations will not instantiate TTS providers or require API keys.

## Data Flow

For shell completion and voice-pack operations, the CLI will resolve config defaults as it does today, then handle these metadata-only operations before provider creation. Voice-pack loading will use `importlib.resources` so packaged wheels and editable source installs behave consistently.

## Error Handling

- Unsupported completion shells will report valid shell names.
- Unknown voice-pack names will report available pack names.
- Malformed bundled YAML will raise a configuration-style error, though this should only occur from a packaging/development bug.

## Testing

Add CLI tests to verify:

- completion script output succeeds for supported shells without creating providers;
- invalid completion shells fail cleanly;
- voice packs list/show without creating providers;
- unknown voice-pack names fail cleanly.

Run the repository's canonical verifier: `make checkall`.
