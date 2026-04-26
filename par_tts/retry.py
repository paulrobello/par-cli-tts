"""Retry helpers for provider operations."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RetryPolicy:
    """Retry configuration for provider operations.

    ``retry_attempts`` is the number of retries after the initial attempt.
    A value of 0 means run once with no retry.
    """

    retry_attempts: int = 0
    backoff_seconds: float = 0.0

    def __post_init__(self) -> None:
        if self.retry_attempts < 0:
            raise ValueError("retry_attempts must be >= 0")
        if self.backoff_seconds < 0:
            raise ValueError("backoff_seconds must be >= 0")

    @property
    def total_attempts(self) -> int:
        """Total attempts including the first try."""
        return self.retry_attempts + 1

    def delay_for_retry(self, retry_number: int) -> float:
        """Return exponential backoff delay for retry number 1..N."""
        if self.backoff_seconds <= 0:
            return 0.0
        return self.backoff_seconds * (2 ** (retry_number - 1))


def run_with_retries(operation_fn: Callable[[], T], policy: RetryPolicy, *, operation: str) -> T:
    """Run an operation with retry/backoff.

    Args:
        operation_fn: Zero-argument callable to execute.
        policy: Retry policy.
        operation: Human-readable operation name used in logs.

    Returns:
        The operation result.

    Raises:
        Exception: Re-raises the final operation exception when all retries fail.
    """
    for attempt in range(1, policy.total_attempts + 1):
        try:
            return operation_fn()
        except Exception as exc:
            if attempt >= policy.total_attempts:
                raise
            retry_number = attempt
            delay = policy.delay_for_retry(retry_number)
            _logger.warning(
                "Retrying %s after failure (%s/%s): %s",
                operation,
                retry_number,
                policy.retry_attempts,
                exc,
            )
            if delay > 0:
                time.sleep(delay)

    raise RuntimeError("unreachable retry state")
