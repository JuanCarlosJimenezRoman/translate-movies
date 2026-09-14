"""Diarizacion (deteccion de hablantes) con pyannote.audio (Fase 2)."""

from movie_translator.transcription.diarization.diarize import (
    DEFAULT_DEVICE,
    DEFAULT_MODEL,
    diarize_audio,
)
from movie_translator.transcription.diarization.errors import DiarizationError
from movie_translator.transcription.diarization.speakers import (
    SpeakerInfo,
    load_speakers,
    save_speakers,
)
from movie_translator.transcription.diarization.turns import SpeakerTurn, assign_speakers

__all__ = [
    "DEFAULT_DEVICE",
    "DEFAULT_MODEL",
    "DiarizationError",
    "SpeakerInfo",
    "SpeakerTurn",
    "assign_speakers",
    "diarize_audio",
    "load_speakers",
    "save_speakers",
]
