"""Orquestador del pipeline: encadena las etapas sobre un Project."""

from movie_translator.core.pipeline.extraction import ORIGINAL_AUDIO_FILENAME, run_extraction
from movie_translator.core.pipeline.transcription import TRANSCRIPT_FILENAME, run_transcription

__all__ = [
    "ORIGINAL_AUDIO_FILENAME",
    "TRANSCRIPT_FILENAME",
    "run_extraction",
    "run_transcription",
]
