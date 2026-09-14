"""Transcripcion con faster-whisper."""

from movie_translator.transcription.whisper.errors import TranscriptionError
from movie_translator.transcription.whisper.transcribe import (
    DEFAULT_COMPUTE_TYPE,
    DEFAULT_DEVICE,
    DEFAULT_MODEL_SIZE,
    DEFAULT_MODELS_DIR,
    DEFAULT_VAD_PARAMETERS,
    transcribe_audio,
)

__all__ = [
    "DEFAULT_COMPUTE_TYPE",
    "DEFAULT_DEVICE",
    "DEFAULT_MODELS_DIR",
    "DEFAULT_MODEL_SIZE",
    "DEFAULT_VAD_PARAMETERS",
    "TranscriptionError",
    "transcribe_audio",
]
