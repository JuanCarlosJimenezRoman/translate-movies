"""Orquestador del pipeline: encadena las etapas sobre un Project."""

from movie_translator.core.pipeline.extraction import ORIGINAL_AUDIO_FILENAME, run_extraction
from movie_translator.core.pipeline.subtitles import run_subtitles, subtitles_filename
from movie_translator.core.pipeline.transcription import TRANSCRIPT_FILENAME, run_transcription
from movie_translator.core.pipeline.translation import (
    DEFAULT_BATCH_SIZE,
    TRANSLATED_FILENAME,
    run_translation,
)

__all__ = [
    "DEFAULT_BATCH_SIZE",
    "ORIGINAL_AUDIO_FILENAME",
    "TRANSCRIPT_FILENAME",
    "TRANSLATED_FILENAME",
    "run_extraction",
    "run_subtitles",
    "run_transcription",
    "run_translation",
    "subtitles_filename",
]
