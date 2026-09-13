"""Nombres y estados de las etapas del pipeline (ver docs/ARCHITECTURE.md)."""

from __future__ import annotations

from enum import Enum


class StageName(str, Enum):
    """Una etapa del pipeline, en el orden en que se ejecutan."""

    EXTRACTION = "extraction"
    SEPARATION = "separation"
    TRANSCRIPTION = "transcription"
    DIARIZATION = "diarization"
    TRANSLATION = "translation"
    TTS = "tts"
    MIXING = "mixing"
    ENCODING = "encoding"


# Orden real de ejecucion. Se usa para saber cual es la "siguiente" etapa
# pendiente y para renderizar el progreso (ver Project.pending_stage / summary).
STAGE_ORDER: tuple[StageName, ...] = (
    StageName.EXTRACTION,
    StageName.SEPARATION,
    StageName.TRANSCRIPTION,
    StageName.DIARIZATION,
    StageName.TRANSLATION,
    StageName.TTS,
    StageName.MIXING,
    StageName.ENCODING,
)


class StageStatus(str, Enum):
    """Estado de una etapa para una pelicula/proyecto dado."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


STAGE_STATUS_SYMBOL: dict[StageStatus, str] = {
    StageStatus.COMPLETED: "✓",  # check
    StageStatus.RUNNING: "→",  # arrow
    StageStatus.PENDING: "○",  # circle
    StageStatus.FAILED: "✗",  # cross
}
