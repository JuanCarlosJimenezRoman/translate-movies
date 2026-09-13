"""Orquestador del pipeline: encadena las etapas sobre un Project."""

from movie_translator.core.pipeline.extraction import ORIGINAL_AUDIO_FILENAME, run_extraction

__all__ = ["ORIGINAL_AUDIO_FILENAME", "run_extraction"]
