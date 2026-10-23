"""A minimal reachability probe for the local Ollama service.

The backend stays responsive when Ollama is down (see ADR 0003): processing is
reported as not ready, while recording and transcription continue. This probe is
deliberately cheap — it answers one question, "is Ollama reachable right now?",
with a short timeout so ``/health`` never blocks.
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

# Keep this well under the /health budget so an unreachable Ollama never makes the
# health check hang.
DEFAULT_TIMEOUT_SECONDS = 2.0


def check_ollama(
    base_url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    transport: httpx.BaseTransport | None = None,
) -> bool:
    """Return ``True`` if Ollama answers its tags endpoint, ``False`` otherwise."""

    url = base_url.rstrip("/") + "/api/tags"
    try:
        with httpx.Client(timeout=timeout, transport=transport) as client:
            response = client.get(url)
        return response.status_code == 200
    except httpx.HTTPError as error:
        logger.debug("Ollama probe to %s failed: %s", url, error)
        return False
