"""FastAPI entrypoint for the Voice Journal backend.

Phase 3 wires up two endpoints:

* ``GET /health`` — always returns 200 while the API is responsive, reporting
  transcription and processing readiness separately (see ADR 0003) so an Ollama
  outage never blocks recording or transcription.
* ``POST /transcribe`` — accepts a Recording, returns its Transcript and the
  backend-measured duration, then discards the audio unless ``RETAIN_AUDIO=true``.

The Whisper model is loaded once at startup so device and model problems surface
before the Author records.
"""

from __future__ import annotations

import logging
import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile

from backend.config import Settings, get_settings
from backend.ollama import check_ollama
from backend.stt import (
    AudioTooLongError,
    AudioTooShortError,
    EmptyTranscriptError,
    Transcriber,
    UnreadableAudioError,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _load_transcriber(settings: Settings) -> Transcriber | None:
    """Load the Whisper model, returning ``None`` (loudly) if it fails.

    Loading at startup means a bad model size or missing device surfaces here,
    not on the Author's first recording. A failure leaves the API responsive in a
    degraded state rather than crashing the process.
    """

    try:
        return Transcriber.load(settings)
    except Exception:
        logger.exception(
            "Failed to load the Whisper model '%s'; transcription is unavailable. "
            "Check WHISPER_MODEL and WHISPER_DEVICE.",
            settings.whisper_model,
        )
        return None


@asynccontextmanager
async def _lifespan(app: FastAPI):
    settings = app.state.settings
    app.state.transcriber = _load_transcriber(settings)
    if check_ollama(settings.ollama_base_url):
        logger.info("Ollama is reachable at %s.", settings.ollama_base_url)
    else:
        logger.warning(
            "Ollama is unreachable at %s; processing will be degraded until it is "
            "available. Recording and transcription are unaffected.",
            settings.ollama_base_url,
        )
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="Voice Journal", lifespan=_lifespan)
    app.state.settings = settings
    app.state.transcriber = None

    @app.get("/health")
    def health() -> dict:
        transcriber = app.state.transcriber
        transcription_ready = transcriber is not None
        processing_ready = check_ollama(app.state.settings.ollama_base_url)
        status = "ready" if transcription_ready and processing_ready else "degraded"
        return {
            "status": status,
            "transcription": {
                "ready": transcription_ready,
                "device": transcriber.device if transcriber else None,
            },
            "processing": {"ready": processing_ready},
        }

    @app.post("/transcribe")
    async def transcribe(audio: Annotated[UploadFile, File()]) -> dict:
        transcriber = app.state.transcriber
        if transcriber is None:
            raise HTTPException(
                status_code=503,
                detail="Transcription is unavailable. The model failed to load.",
            )

        content = await audio.read()
        if not content:
            raise HTTPException(status_code=422, detail="The uploaded audio was empty.")

        suffix = Path(audio.filename or "").suffix or ".webm"
        descriptor, audio_path = tempfile.mkstemp(prefix="recording-", suffix=suffix)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(content)
            result = transcriber.transcribe(audio_path)
        except (
            AudioTooShortError,
            EmptyTranscriptError,
            UnreadableAudioError,
        ) as error:
            raise HTTPException(status_code=422, detail=str(error))
        except AudioTooLongError as error:
            raise HTTPException(status_code=413, detail=str(error))
        finally:
            if app.state.settings.retain_audio:
                logger.info("RETAIN_AUDIO is set; keeping recording at %s", audio_path)
            else:
                _discard(audio_path)

        return {
            "transcript": result.transcript,
            "audio_duration_seconds": result.audio_duration_seconds,
        }

    return app


def _discard(audio_path: str) -> None:
    try:
        os.remove(audio_path)
    except OSError:
        logger.warning("Could not delete temporary recording at %s", audio_path)


app = create_app()
