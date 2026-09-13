"""Segmento de transcripcion: una linea de dialogo con su timing."""

from __future__ import annotations

import json
from pathlib import Path

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


def save_segments(segments: list[Segment], path: Path) -> None:
    """Guarda una lista de segmentos como JSON (ver docs/ARCHITECTURE.md, seccion 6)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [segment.model_dump(mode="json") for segment in segments]
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_segments(path: Path) -> list[Segment]:
    """Carga una lista de segmentos guardada con save_segments()."""
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo de segmentos: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [Segment.model_validate(item) for item in payload]
