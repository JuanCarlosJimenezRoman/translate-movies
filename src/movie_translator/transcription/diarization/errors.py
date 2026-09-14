"""Errores especificos de la etapa de diarizacion."""

from __future__ import annotations


class DiarizationError(RuntimeError):
    """Fallo cargando el pipeline de pyannote o diarizando el audio.

    Incluye tanto el 401/403 "gated" de Hugging Face (falta aceptar la
    licencia del modelo o el HF_TOKEN no tiene acceso -- ver
    docs/estado-proyecto y docs/DECISIONES.md) como cualquier otro fallo de
    pyannote.audio en si.
    """
