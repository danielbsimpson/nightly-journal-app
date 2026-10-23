"""Tests for the HTTP contract: ``GET /health`` and ``POST /transcribe``.

The Whisper model and Ollama are external boundaries. The model is injected as a
fake Transcriber via ``app.state``; Ollama's probe is replaced with a stub. The
temp-file lifecycle is exercised against the real filesystem through the endpoint.
"""

from __future__ import annotations

import os

from fastapi.testclient import TestClient

from backend import main, stt
from backend.config import Settings


class _FakeTranscriber:
    def __init__(self, *, device="cpu", result=None, error=None):
        self.device = device
        self._result = result
        self._error = error
        self.last_path = None

    def transcribe(self, audio_path):
        self.last_path = audio_path
        if self._error is not None:
            raise self._error
        return self._result


def _client(monkeypatch, *, transcriber, ollama_ready=True, settings=None):
    settings = settings or Settings()
    monkeypatch.setattr(main, "check_ollama", lambda *args, **kwargs: ollama_ready)
    app = main.create_app(settings)
    app.state.transcriber = transcriber
    return TestClient(app)


def _audio_upload(content: bytes = b"fake-audio-bytes"):
    return {"audio": ("recording.webm", content, "audio/webm")}


# ─── GET /health ────────────────────────────────────────────────────────

def test_health_is_ready_when_model_and_ollama_are_up(monkeypatch):
    client = _client(
        monkeypatch,
        transcriber=_FakeTranscriber(device="cuda"),
        ollama_ready=True,
    )

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["transcription"] == {"ready": True, "device": "cuda"}
    assert body["processing"] == {"ready": True}


def test_health_is_degraded_when_ollama_is_down(monkeypatch):
    client = _client(
        monkeypatch,
        transcriber=_FakeTranscriber(device="cpu"),
        ollama_ready=False,
    )

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["transcription"]["ready"] is True
    assert body["processing"]["ready"] is False


def test_health_stays_responsive_when_the_model_failed_to_load(monkeypatch):
    client = _client(monkeypatch, transcriber=None, ollama_ready=True)

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["transcription"] == {"ready": False, "device": None}
    assert body["processing"]["ready"] is True


# ─── POST /transcribe ───────────────────────────────────────────────────

def test_transcribe_returns_transcript_and_measured_duration(monkeypatch):
    result = stt.TranscriptionResult(transcript="Hello there.", audio_duration_seconds=4.2)
    client = _client(monkeypatch, transcriber=_FakeTranscriber(result=result))

    response = client.post("/transcribe", files=_audio_upload())

    assert response.status_code == 200
    assert response.json() == {"transcript": "Hello there.", "audio_duration_seconds": 4.2}


def test_transcribe_deletes_the_recording_by_default(monkeypatch):
    transcriber = _FakeTranscriber(
        result=stt.TranscriptionResult("A quiet evening.", 3.0)
    )
    client = _client(monkeypatch, transcriber=transcriber)

    client.post("/transcribe", files=_audio_upload())

    assert transcriber.last_path is not None
    assert not os.path.exists(transcriber.last_path)


def test_transcribe_retains_the_recording_when_configured(monkeypatch):
    transcriber = _FakeTranscriber(
        result=stt.TranscriptionResult("A quiet evening.", 3.0)
    )
    client = _client(
        monkeypatch,
        transcriber=transcriber,
        settings=Settings(retain_audio=True),
    )

    try:
        client.post("/transcribe", files=_audio_upload())
        assert transcriber.last_path is not None
        assert os.path.exists(transcriber.last_path)
    finally:
        if transcriber.last_path and os.path.exists(transcriber.last_path):
            os.remove(transcriber.last_path)


def test_transcribe_is_unavailable_without_a_loaded_model(monkeypatch):
    client = _client(monkeypatch, transcriber=None)

    response = client.post("/transcribe", files=_audio_upload())

    assert response.status_code == 503


def test_transcribe_rejects_audio_under_the_minimum(monkeypatch):
    transcriber = _FakeTranscriber(error=stt.AudioTooShortError(1.0, 2.0))
    client = _client(monkeypatch, transcriber=transcriber)

    response = client.post("/transcribe", files=_audio_upload())

    assert response.status_code == 422


def test_transcribe_rejects_empty_transcripts(monkeypatch):
    transcriber = _FakeTranscriber(error=stt.EmptyTranscriptError(5.0))
    client = _client(monkeypatch, transcriber=transcriber)

    response = client.post("/transcribe", files=_audio_upload())

    assert response.status_code == 422


def test_transcribe_rejects_undecodable_audio(monkeypatch):
    transcriber = _FakeTranscriber(error=stt.UnreadableAudioError())
    client = _client(monkeypatch, transcriber=transcriber)

    response = client.post("/transcribe", files=_audio_upload())

    assert response.status_code == 422
