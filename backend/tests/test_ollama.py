"""Tests for the Ollama reachability probe.

Ollama is an external HTTP service, so it is faked with an httpx MockTransport.
"""

from __future__ import annotations

import httpx

from backend import ollama


def _probe_with(handler, **kwargs) -> bool:
    return ollama.check_ollama(
        "http://localhost:11434",
        transport=httpx.MockTransport(handler),
        **kwargs,
    )


def test_reports_reachable_when_ollama_answers():
    assert _probe_with(lambda request: httpx.Response(200, json={"models": []})) is True


def test_reports_unreachable_on_server_error():
    assert _probe_with(lambda request: httpx.Response(500)) is False


def test_reports_unreachable_when_connection_refused():
    def refuse(request):
        raise httpx.ConnectError("connection refused", request=request)

    assert _probe_with(refuse) is False


def test_reports_unreachable_on_timeout():
    def time_out(request):
        raise httpx.TimeoutException("timed out", request=request)

    assert _probe_with(time_out) is False
