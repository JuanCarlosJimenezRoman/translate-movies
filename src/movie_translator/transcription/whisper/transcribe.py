"""Transcripcion de audio con faster-whisper (ver docs/ARCHITECTURE.md, Fase 1).

El modelo se descarga la primera vez que se usa (a `models_dir`) y queda
cacheado ahi para corridas siguientes. Ver docs/DECISIONES.md sobre el
tamano de modelo elegido por defecto.
"""

from __future__ import annotations

import math
from pathlib import Path

from faster_whisper import WhisperModel

from movie_translator.core.models.segment import Segment
from movie_translator.transcription.whisper.errors import TranscriptionError

# "small": mejor balance calidad/velocidad en CPU para este proyecto (ver
# docs/DECISIONES.md). Configurable por llamada/CLI, esto es solo el default.
DEFAULT_MODEL_SIZE = "small"
DEFAULT_MODELS_DIR = Path("models")
DEFAULT_DEVICE = "cpu"
# int8: cuantizacion que acelera bastante la inferencia en CPU a cambio de
# una perdida de calidad minima. En GPU se usaria "float16" (Fase 7).
DEFAULT_COMPUTE_TYPE = "int8"


def _confidence_from_logprob(avg_logprob: float) -> float:
    """Aproxima una confianza en [0, 1] a partir del avg_logprob de whisper.

    avg_logprob no es una probabilidad (es un log-promedio, tipicamente
    negativo), pero exp(avg_logprob) es la aproximacion estandar para
    mostrar algo interpretable como "que tan seguro estaba el modelo".
    """
    return max(0.0, min(1.0, math.exp(avg_logprob)))


def transcribe_audio(
    audio_path: Path,
    *,
    model_size: str = DEFAULT_MODEL_SIZE,
    language: str | None = None,
    models_dir: Path = DEFAULT_MODELS_DIR,
    device: str = DEFAULT_DEVICE,
    compute_type: str = DEFAULT_COMPUTE_TYPE,
) -> list[Segment]:
    """Transcribe `audio_path` y devuelve sus segmentos, ordenados por tiempo.

    `language` es el codigo de idioma de origen (ej. "en"); si se conoce de
    antemano (viene de `Project.source_language`), pasarlo evita que Whisper
    tenga que detectarlo y mejora la consistencia del resultado.

    Lanza FileNotFoundError si `audio_path` no existe, y TranscriptionError
    si faster-whisper falla cargando el modelo o transcribiendo.
    """
    if not audio_path.exists():
        raise FileNotFoundError(f"No existe el archivo de audio: {audio_path}")

    models_dir.mkdir(parents=True, exist_ok=True)

    try:
        model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            download_root=str(models_dir),
        )
        segments_iter, _info = model.transcribe(
            str(audio_path),
            language=language,
            vad_filter=True,
        )
        return [
            Segment(
                start=seg.start,
                end=seg.end,
                text=seg.text.strip(),
                confidence=_confidence_from_logprob(seg.avg_logprob),
            )
            for seg in segments_iter
        ]
    except Exception as exc:
        raise TranscriptionError(
            f"Fallo transcribiendo {audio_path} con el modelo '{model_size}': {exc}"
        ) from exc
