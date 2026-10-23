"""Tests for the llama-server reachability probe.

llama-server is an external HTTP service, so it is faked with an httpx
MockTransport.
"""

from __future__ import annotations

import httpx

from backend import llm


def _probe_with(handler, **kwargs) -> bool:
    return llm.check_llama_server(
        "http://localhost:8080",
        transport=httpx.MockTransport(handler),
        **kwargs,
    )


def test_reports_ready_when_llama_server_answers():
    assert _probe_with(lambda request: httpx.Response(200, json={"status": "ok"})) is True


def test_reports_not_ready_while_model_is_loading():
    assert _probe_with(lambda request: httpx.Response(503, json={"status": "loading model"})) is False


def test_reports_unreachable_when_connection_refused():
    def refuse(request):
        raise httpx.ConnectError("connection refused", request=request)

    assert _probe_with(refuse) is False


def test_reports_unreachable_on_timeout():
    def time_out(request):
        raise httpx.TimeoutException("timed out", request=request)

    assert _probe_with(time_out) is False
