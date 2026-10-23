"""A minimal reachability probe for the local llama.cpp server (llama-server).

The backend stays responsive when the LLM server is down (see ADR 0003):
processing is reported as not ready, while recording and transcription continue.
This probe is deliberately cheap — it answers one question, "is llama-server
ready right now?", with a short timeout so ``/health`` never blocks.

Phase 4 grows this module into the full processing client; for now it only
reports readiness.
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

# Keep this well under the /health budget so an unreachable server never makes the
# health check hang.
DEFAULT_TIMEOUT_SECONDS = 2.0


def check_llama_server(
    base_url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    transport: httpx.BaseTransport | None = None,
) -> bool:
    """Return ``True`` if llama-server reports ready, ``False`` otherwise.

    llama-server answers ``GET /health`` with 200 once the model is loaded and
    503 while it is still loading, so a 200 means genuinely ready to process.
    """

    url = base_url.rstrip("/") + "/health"
    try:
        with httpx.Client(timeout=timeout, transport=transport) as client:
            response = client.get(url)
        return response.status_code == 200
    except httpx.HTTPError as error:
        logger.debug("llama-server probe to %s failed: %s", url, error)
        return False
