"""Public provider factory helpers."""

from __future__ import annotations

import os
from typing import Any

from par_tts.errors import ErrorType, TTSError
from par_tts.providers.base import TTSProvider
from par_tts.providers.registry import get_provider_plugin


def create_provider(
    name: str,
    *,
    api_key: str | None = None,
    provider_kwargs: dict[str, Any] | None = None,
    **kwargs: Any,
) -> TTSProvider:
    """Create a provider instance from plugin metadata.

    Args:
        name: Provider registry name.
        api_key: Explicit API key. If omitted, declared environment variables
            are checked for providers that require keys.
        provider_kwargs: Provider constructor keyword arguments.
        **kwargs: Additional provider constructor keyword arguments merged over
            ``provider_kwargs`` for convenience.

    Returns:
        Initialized provider instance.

    Raises:
        TTSError: If the provider is unknown, requires a missing API key, or
            cannot be initialized.
    """
    try:
        plugin = get_provider_plugin(name)
    except ValueError as exc:
        raise TTSError(str(exc), ErrorType.INVALID_PROVIDER) from exc

    resolved_kwargs = {**(provider_kwargs or {}), **kwargs}
    resolved_api_key = api_key if api_key is not None else _api_key_from_environment(plugin.api_key_env_vars)

    if plugin.requires_api_key and not resolved_api_key:
        env_help = ", ".join(plugin.api_key_env_vars) or "a provider-specific API key"
        raise TTSError(f"API key required for {name}. Set one of: {env_help}", ErrorType.MISSING_API_KEY)

    try:
        if plugin.requires_api_key:
            return plugin.provider_class(resolved_api_key, **resolved_kwargs)
        return plugin.provider_class(api_key=resolved_api_key, **resolved_kwargs)
    except Exception as exc:
        raise TTSError(f"Failed to initialize {name} provider", ErrorType.PROVIDER_ERROR) from exc


def _api_key_from_environment(env_vars: tuple[str, ...]) -> str | None:
    for env_var in env_vars:
        value = os.getenv(env_var)
        if value:
            return value
    return None
