"""Shared helper for Anthropic SDK calls from decision modules.

Centralises three concerns the four decision sites used to handle silently:

1. **Timeout.** Every SDK call goes through `_make_client`, which builds an
   `anthropic.Anthropic` instance with a 10 second request timeout. The SDK
   default is 10 minutes, which can stall a phase if the network drops.
2. **Single retry.** `call_with_retry` reruns the request once on the
   network-class errors the SDK exposes (`APIConnectionError`,
   `APITimeoutError`). Other errors (rate limit, auth, schema) are not
   retried; they are typically deterministic and a second call wastes a token.
3. **Structured failure logging.** When a call fails after the retry, the
   helper invokes the optional `emit` callback with a `decision.anthropic_failed`
   event carrying the error class and HTTP status code. The role worker passes
   `state.emit` so the failure surfaces on the SSE stream instead of falling
   through silently to the deterministic stub.

Decision modules call `call_with_retry` and re-raise on failure; their callers
catch the exception and fall back to the stub path. The fallback itself is the
contract; this helper just makes the failure visible.
"""

from __future__ import annotations

import os
from typing import Any, Callable, TypeVar

DEFAULT_TIMEOUT_S = 10.0
RETRYABLE_ERROR_NAMES = ("APIConnectionError", "APITimeoutError")

# Model id used by every decision site. Centralised so a model refresh is one
# edit, not four. Override at runtime by exporting `HACKSIM_MODEL`. When
# Anthropic ships a successor we update this constant and rerun the agent
# tests; the env var lets a local user pin to a previous version without
# editing source.
DEFAULT_MODEL = "claude-haiku-4-5-20251001"


def get_model() -> str:
    """Return the model id every Anthropic call site should use.

    Resolves `HACKSIM_MODEL` if set, falling back to `DEFAULT_MODEL`. Read at
    call time, not import time, so a process spawned with the env var picks
    up the override without a restart of the test runner.
    """
    return os.environ.get("HACKSIM_MODEL", DEFAULT_MODEL)

EmitFn = Callable[[str, dict[str, Any]], None]
T = TypeVar("T")


def make_client(api_key: str, *, timeout: float = DEFAULT_TIMEOUT_S):
    """Build an `anthropic.Anthropic` client with a sane request timeout.

    Lazy-imports the SDK so this module stays importable when the SDK is
    missing (CI runs the stub path).

    `max_retries=0` disables the SDK's internal retry loop. `call_with_retry`
    is our single retry path; without this, the SDK's default of 2 silently
    triples wall-clock time (one timeout becomes three) and a slow call can
    exceed the BUILD phase even when a single attempt would have succeeded.
    """
    import anthropic

    return anthropic.Anthropic(api_key=api_key, timeout=timeout, max_retries=0)


def call_with_retry(
    fn: Callable[[], T],
    *,
    operation: str,
    emit: EmitFn | None = None,
) -> T:
    """Run `fn()`, retry once on transient SDK errors, raise on second failure.

    On any exception that surfaces after the retry, emits one
    `decision.anthropic_failed` event before re-raising. The caller catches
    and falls back to the deterministic stub.
    """
    try:
        return fn()
    except Exception as first:
        if not _is_retryable(first):
            _emit_failure(emit, operation, first, attempts=1)
            raise
    try:
        return fn()
    except Exception as second:
        _emit_failure(emit, operation, second, attempts=2)
        raise


def _is_retryable(exc: BaseException) -> bool:
    """True for the connection-class errors the Anthropic SDK exposes."""
    return type(exc).__name__ in RETRYABLE_ERROR_NAMES


def _emit_failure(
    emit: EmitFn | None,
    operation: str,
    exc: BaseException,
    *,
    attempts: int,
) -> None:
    if emit is None:
        return
    payload: dict[str, Any] = {
        "operation": operation,
        "error_class": type(exc).__name__,
        "error": str(exc)[:200],
        "attempts": attempts,
    }
    status = getattr(exc, "status_code", None)
    if isinstance(status, int):
        payload["status_code"] = status
    emit("decision.anthropic_failed", payload)
