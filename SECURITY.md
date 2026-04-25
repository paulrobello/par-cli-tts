# Security Policy

## Reporting Vulnerabilities

If you discover a security vulnerability in PAR CLI TTS, please report it responsibly:

- **Email**: [probello@gmail.com](mailto:probello@gmail.com)
- **GitHub**: Open a private security advisory at [github.com/paulrobello/par-cli-tts/security](https://github.com/paulrobello/par-cli-tts/security)

Please do not file public issues for security vulnerabilities.

### What to Include

- Description of the vulnerability
- Steps to reproduce
- Affected versions (if known)
- Potential impact

You should receive a response within 48 hours.

## Security Practices

### API Key Handling

PAR CLI TTS handles API keys for multiple cloud TTS providers. The project takes the following precautions:

- **Environment variables**: API keys are read from environment variables, not hardcoded
- **Config file**: API keys stored in `config.yaml` are user-controlled and local
- **Debug sanitization**: Debug output masks API keys via `sanitize_debug_output()`
- **No credential logging**: Authentication credentials are never written to log output

### Model Downloads

Offline models (Kokoro ONNX) are downloaded with integrity verification:

- **SHA256 checksums**: All downloaded model files are verified against expected checksums
- **Atomic downloads**: Temporary files prevent corruption from interrupted downloads
- **HTTPS**: All downloads use HTTPS transport

### Input Handling

- **File path validation**: `validate_file_path()` checks paths for security issues
- **YAML safety**: Configuration files are loaded with `yaml.safe_load()` to prevent code injection
- **Config validation**: Pydantic models use `extra = "forbid"` to reject unexpected fields

### Library Usage

When used as a library, PAR CLI TTS:

- Raises typed exceptions (`TTSError`) instead of calling `sys.exit()`
- Does not import CLI-only dependencies (Rich, Typer) into library code
- Uses `stdlib logging` instead of console output

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.5.x   | Yes       |
| 0.4.x   | Yes       |
| < 0.4   | No        |

## Security Updates

Security fixes are backported to the latest minor release in each supported major version. Update to the latest patch release to receive security fixes:

```bash
uv tool upgrade par-cli-tts
```
