"""Segmento de transcripcion: una linea de dialogo con su timing."""

from __future__ import annotations

from pydantic import BaseModel, Field, ValidationInfo, field_validator


class Segment(BaseModel):
    """Una linea de dialogo transcrita (ver docs/ARCHITECTURE.md, seccion 6).

    `speaker` queda en None hasta que corre la diarizacion (Fase 2); en la
    Fase 1 (solo subtitulos) los segmentos se generan sin hablante asignado.
    """

    start: float = Field(ge=0, description="Timestamp de inicio, en segundos")
    end: float = Field(ge=0, description="Timestamp de fin, en segundos")
    text: str
    speaker: str | None = Field(
        default=None, description="Ej. 'SPEAKER_01' (diarizacion, Fase 2)"
    )
    confidence: float | None = Field(
        default=None, ge=0, le=1, description="Confianza del modelo de ASR"
    )

    @field_validator("end")
    @classmethod
    def _end_after_start(cls, end: float, info: ValidationInfo) -> float:
        start = info.data.get("start")
        if start is not None and end < start:
            raise ValueError(f"end ({end}) no puede ser menor que start ({start})")
        return end

    @property
    def duration(self) -> float:
        return self.end - self.start
