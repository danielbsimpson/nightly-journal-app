"""Tests for the speech-to-text seam.

The Whisper model and the audio decoder are external boundaries (an ML runtime
and ffmpeg), so they are injected as fakes. Everything else is real.
"""

from __future__ import annotations

import logging
import types

import numpy as np
import pytest

from backend import stt


class _FakeSegment:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeModel:
    """Stand-in for faster_whisper.WhisperModel."""

    def __init__(self, segments: list[_FakeSegment]) -> None:
        self._segments = segments
        self.calls: list[dict] = []

    def transcribe(self, audio, **kwargs):
        self.calls.append(kwargs)
        info = types.SimpleNamespace(duration=len(audio) / stt.SAMPLE_RATE)
        return iter(self._segments), info


def _make_transcriber(texts, duration_seconds, min_seconds=2.0):
    samples = np.zeros(int(duration_seconds * stt.SAMPLE_RATE), dtype=np.float32)

    def fake_decode(path, sampling_rate=stt.SAMPLE_RATE):
        return samples

    model = _FakeModel([_FakeSegment(t) for t in texts])
    transcriber = stt.Transcriber(
        device="cpu",
        language="en",
        min_seconds=min_seconds,
        model=model,
        decode=fake_decode,
    )
    return transcriber, model


# ─── Device resolution ──────────────────────────────────────────────────

def test_auto_prefers_cuda_when_a_gpu_is_present():
    assert stt.resolve_device("auto", cuda_device_count=1) == ("cuda", "float16")


def test_auto_falls_back_to_cpu_with_a_loud_warning(caplog):
    with caplog.at_level(logging.WARNING):
        device, compute_type = stt.resolve_device("auto", cuda_device_count=0)
    assert (device, compute_type) == ("cpu", "int8")
    assert any(record.levelno >= logging.WARNING for record in caplog.records)


def test_explicit_cpu_is_honored_even_with_a_gpu():
    assert stt.resolve_device("cpu", cuda_device_count=4) == ("cpu", "int8")


def test_explicit_cuda_is_honored_even_without_a_gpu():
    assert stt.resolve_device("cuda", cuda_device_count=0) == ("cuda", "float16")


# ─── CUDA → CPU fallback at load time ───────────────────────────────────

def test_auto_falls_back_to_cpu_when_cuda_init_fails():
    attempted = []

    def builder(device, compute_type):
        attempted.append(device)
        if device == "cuda":
            raise RuntimeError("Library cublas64_12.dll is not found")
        return object()

    _model, device = stt._build_with_fallback(builder, "auto", "cuda", "float16")

    assert device == "cpu"
    assert attempted == ["cuda", "cpu"]


def test_explicit_cuda_failure_is_not_swallowed():
    def builder(device, compute_type):
        raise RuntimeError("Library cublas64_12.dll is not found")

    with pytest.raises(RuntimeError):
        stt._build_with_fallback(builder, "cuda", "cuda", "float16")


def test_no_fallback_when_the_device_already_works():
    def builder(device, compute_type):
        return ("model", device)

    model, device = stt._build_with_fallback(builder, "auto", "cuda", "float16")

    assert device == "cuda"
    assert model == ("model", "cuda")


# ─── transcribe() ───────────────────────────────────────────────────────

def test_transcribe_returns_joined_text_and_measured_duration():
    transcriber, _ = _make_transcriber([" Hello", " world."], duration_seconds=5.0)

    result = transcriber.transcribe("recording.webm")

    assert result.transcript == "Hello world."
    assert result.audio_duration_seconds == 5.0


def test_transcribe_rejects_audio_under_the_minimum():
    transcriber, _ = _make_transcriber([" Hi"], duration_seconds=1.0)

    with pytest.raises(stt.AudioTooShortError):
        transcriber.transcribe("recording.webm")


def test_transcribe_rejects_audio_over_ten_minutes():
    transcriber, _ = _make_transcriber([" long"], duration_seconds=601.0)

    with pytest.raises(stt.AudioTooLongError):
        transcriber.transcribe("recording.webm")


def test_transcribe_rejects_empty_transcripts():
    transcriber, _ = _make_transcriber(["   "], duration_seconds=5.0)

    with pytest.raises(stt.EmptyTranscriptError):
        transcriber.transcribe("recording.webm")


def test_transcribe_rejects_undecodable_audio():
    def boom_decode(path, sampling_rate=stt.SAMPLE_RATE):
        raise RuntimeError("ffmpeg could not read the stream")

    transcriber = stt.Transcriber(
        device="cpu",
        language="en",
        min_seconds=2.0,
        model=_FakeModel([]),
        decode=boom_decode,
    )

    with pytest.raises(stt.UnreadableAudioError):
        transcriber.transcribe("corrupt.webm")
