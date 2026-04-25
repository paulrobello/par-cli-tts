"""HTTP client factory for PAR CLI TTS.

This module provides a factory function for creating HTTP clients
with consistent configuration across all providers.
"""

import httpx


def create_http_client(timeout: float = 10.0, verify: bool = True) -> httpx.Client:
    """Create an HTTP client with standard configuration.

    Args:
        timeout: Request timeout in seconds.
        verify: Whether to verify SSL certificates. Defaults to True.

    Returns:
        Configured httpx.Client instance.
    """
    return httpx.Client(verify=verify, timeout=timeout)
