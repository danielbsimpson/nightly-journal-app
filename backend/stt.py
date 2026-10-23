"""Speech-to-text: turn a Recording into a Transcript and its measured duration.

The Whisper model is loaded once at startup (see :meth:`Transcriber.load`) so that
device and model problems surface before the Author records, not on first use. The
duration the backend returns is measured from the decoded audio here — it is the
authoritative value, independent of whatever the browser timed.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from backend.config import MAX_RECORDING_SECONDS, Settings

logger = logging.getLogger(__name__)

# faster-whisper decodes everything to 16 kHz mono; duration is samples / rate.
SAMPLE_RATE = 16000


class TranscriptionError(Exception):
    """Base class for recoverable transcription failures."""


class AudioTooShortError(TranscriptionError):
    """The Recording is below the minimum length to be worth transcribing."""

    def __init__(self, duration: float, minimum: float) -> None:
        self.duration = duration
        self.minimum = minimum
        super().__init__(
            f"Recording is {duration:.2f}s, below the {minimum:.2f}s minimum."
        )


class AudioTooLongError(TranscriptionError):
    """The Recording exceeds the hard ten-minute ceiling."""

    def __init__(self, duration: float, maximum: float) -> None:
        self.duration = duration
        self.maximum = maximum
        super().__init__(
            f"Recording is {duration:.2f}s, above the {maximum:.0f}s maximum."
        )


class EmptyTranscriptError(TranscriptionError):
    """The Recording transcribed to nothing (silence or noise)."""

    def __init__(self, duration: float) -> None:
        self.duration = duration
        super().__init__("Recording produced an empty transcript.")


class UnreadableAudioError(TranscriptionError):
    """The Recording could not be decoded (corrupt or unsupported audio)."""

    def __init__(self) -> None:
        super().__init__("Recording could not be decoded.")


@dataclass(frozen=True)
class TranscriptionResult:
    """A Transcript together with the backend-measured audio duration."""

    transcript: str
    audio_duration_seconds: float


class _WhisperModel(Protocol):
    def transcribe(self, audio, **kwargs): ...


def resolve_device(requested: str, cuda_device_count: int | None = None) -> tuple[str, str]:
    """Resolve the requested device into a (device, compute_type) pair.

    ``auto`` prefers CUDA and falls back to CPU with a loud warning rather than
    crashing. Explicit ``cuda``/``cpu`` are honored as given.
    """

    requested = (requested or "auto").strip().lower()

    if requested == "cpu":
        return "cpu", "int8"
    if requested == "cuda":
        return "cuda", "float16"

    if cuda_device_count is None:
        cuda_device_count = _cuda_device_count()

    if cuda_device_count > 0:
        return "cuda", "float16"

    logger.warning(
        "WHISPER_DEVICE=auto could not find a CUDA device; falling back to CPU. "
        "Transcription will work but run slower."
    )
    return "cpu", "int8"


def _cuda_device_count() -> int:
    try:
        import ctranslate2

        return ctranslate2.get_cuda_device_count()
    except Exception:  # noqa: BLE001 - any failure here means no usable CUDA runtime
        logger.warning("Could not query CUDA devices; assuming none are available.")
        return 0


def _build_and_warm_up(whisper_model_cls, model_size: str, device: str, compute_type: str):
    """Construct a Whisper model and run a tiny inference to surface runtime issues.

    Loading the weights can succeed on a GPU whose CUDA runtime libraries (e.g.
    cuBLAS) are missing; the failure only appears on the first real inference.
    Warming up here forces that failure at startup so it can be handled.
    """

    model = whisper_model_cls(model_size, device=device, compute_type=compute_type)
    warmup = np.zeros(SAMPLE_RATE, dtype=np.float32)
    segments, _info = model.transcribe(warmup)
    for _segment in segments:
        break
    return model


def _build_with_fallback(
    builder: Callable[[str, str], object],
    requested: str,
    device: str,
    compute_type: str,
):
    """Build the model on ``device``, falling back to CPU on CUDA failure.

    The fallback only applies when the device was chosen automatically; an
    explicit ``WHISPER_DEVICE=cuda`` is honored and its failure propagates.
    """

    try:
        return builder(device, compute_type), device
    except Exception:
        if requested != "auto" or device != "cuda":
            raise
        logger.warning(
            "Whisper could not initialise on CUDA; falling back to CPU. "
            "Transcription will work but run slower. Check your CUDA/cuBLAS install."
        )
        return builder("cpu", "int8"), "cpu"


class Transcriber:
    """Transcribes Recordings using a loaded Whisper model."""

    def __init__(
        self,
        *,
        device: str,
        language: str,
        min_seconds: float,
        model: _WhisperModel,
        decode: Callable[..., object],
    ) -> None:
        self.device = device
        self.language = language or None
        self.min_seconds = min_seconds
        self._model = model
        self._decode = decode

    @classmethod
    def load(cls, settings: Settings) -> Transcriber:
        """Build a Transcriber, loading the model at startup.

        The model is resolved from the local Hugging Face cache by size (e.g.
        ``base``), so an already-downloaded model is reused rather than fetched
        again. The model is warmed up here so runtime problems (a bad size, or a
        GPU with a missing CUDA runtime) surface now; in ``auto`` mode a CUDA
        failure falls back to CPU with a loud warning rather than crashing.
        """

        from faster_whisper import WhisperModel, decode_audio

        requested = (settings.whisper_device or "auto").strip().lower()
        device, compute_type = resolve_device(settings.whisper_device)

        def builder(use_device: str, use_compute_type: str):
            logger.info(
                "Loading Whisper model '%s' on %s (%s).",
                settings.whisper_model,
                use_device,
                use_compute_type,
            )
            return _build_and_warm_up(
                WhisperModel, settings.whisper_model, use_device, use_compute_type
            )

        model, device = _build_with_fallback(builder, requested, device, compute_type)
        return cls(
            device=device,
            language=settings.whisper_language,
            min_seconds=settings.min_recording_seconds,
            model=model,
            decode=decode_audio,
        )

    def transcribe(self, audio_path) -> TranscriptionResult:
        """Transcribe the audio at ``audio_path``.

        Raises :class:`AudioTooShortError`, :class:`AudioTooLongError`, or
        :class:`EmptyTranscriptError` for Recordings that cannot yield a usable
        Transcript.
        """

        audio = self._decode_audio(audio_path)
        duration = len(audio) / SAMPLE_RATE

        if duration < self.min_seconds:
            raise AudioTooShortError(duration, self.min_seconds)
        if duration > MAX_RECORDING_SECONDS:
            raise AudioTooLongError(duration, MAX_RECORDING_SECONDS)

        segments, _info = self._model.transcribe(audio, language=self.language)
        transcript = "".join(segment.text for segment in segments).strip()

        if not transcript:
            raise EmptyTranscriptError(duration)

        return TranscriptionResult(
            transcript=transcript,
            audio_duration_seconds=duration,
        )

    def _decode_audio(self, audio_path):
        try:
            return self._decode(audio_path, sampling_rate=SAMPLE_RATE)
        except Exception as error:
            raise UnreadableAudioError() from error
