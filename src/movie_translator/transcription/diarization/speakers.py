"""Mapa de hablantes (`speakers.json`, ver docs/ARCHITECTURE.md seccion 6).

`run_diarization` lo crea/actualiza con un placeholder (character=None) por
cada SPEAKER_NN nuevo que detecta, sin pisar los que ya tienen nombre. El
checkpoint humano ('movie-translator name-speakers', prompt interactivo por
hablante) es quien completa `character`. `voice` es de Fase 3 (TTS): existe
desde ya en el modelo para no tener que migrar el archivo mas adelante, pero
nada en Fase 2 lo lee ni lo escribe.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel


class SpeakerInfo(BaseModel):
    character: str | None = None
    voice: str | None = None


def load_speakers(path: Path) -> dict[str, SpeakerInfo]:
    """Carga el mapa de hablantes. Si todavia no existe, devuelve uno vacio."""
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {label: SpeakerInfo.model_validate(info) for label, info in payload.items()}


def save_speakers(speakers: dict[str, SpeakerInfo], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {label: info.model_dump(mode="json") for label, info in speakers.items()}
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
