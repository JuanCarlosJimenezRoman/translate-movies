"""Errores especificos de la etapa de transcripcion."""

from __future__ import annotations


class TranscriptionError(RuntimeError):
    """Fallo cargando el modelo de Whisper o transcribiendo el audio."""
