"""Diarizacion con pyannote.audio (ver docs/ARCHITECTURE.md, Fase 2).

pyannote.audio es un extra opcional (`uv sync --extra diarization`): el
import real de `pyannote.audio` pasa dentro de `diarize_audio`, no al
importar este modulo, para que el resto del CLI funcione sin tenerlo
instalado (mismo patron que los proveedores de traduccion).

A diferencia de los modelos de Whisper (publicos), los modelos de pyannote
usados aca son "gated" en Hugging Face: hay que aceptar su licencia estando
logueado y usar un HF_TOKEN con acceso, o pyannote falla con 401/403 (no
confundir con el 403 del proxy de red del entorno remoto de Claude, que es
otro problema -- ver docs/estado-proyecto.md).
"""

from __future__ import annotations

import os
from pathlib import Path

from movie_translator.transcription.diarization.errors import DiarizationError
from movie_translator.transcription.diarization.turns import SpeakerTurn

# Ver https://huggingface.co/pyannote/speaker-diarization-3.1 -- requiere
# aceptar la licencia de este modelo y de pyannote/segmentation-3.0.
DEFAULT_MODEL = "pyannote/speaker-diarization-3.1"
DEFAULT_DEVICE = "cpu"


def _load_pipeline(pipeline_cls: type, model: str, token: str):
    """Carga el pipeline soportando ambas APIs de pyannote.audio.

    pyannote.audio 4.0+ renombro el parametro `use_auth_token` de
    `Pipeline.from_pretrained()` a `token` (alineado con huggingface_hub).
    `pyproject.toml` solo fija `pyannote.audio>=3.3`, asi que este helper
    prueba la firma nueva primero y cae a la vieja si el kwarg no existe,
    para no depender de que version este instalada.
    """
    try:
        return pipeline_cls.from_pretrained(model, token=token)
    except TypeError:
        return pipeline_cls.from_pretrained(model, use_auth_token=token)


def _run_pipeline(pipeline: object, audio_path: Path):
    """Corre `pipeline` sobre `audio_path`, con fallback si falta torchcodec.

    pyannote.audio 4.0+ decodifica el audio con torchcodec cuando se le pasa
    una ruta de archivo, y torchcodec necesita una build de FFmpeg
    "full-shared" (con las DLLs) que muchas instalaciones de Windows no
    tienen -- falla con "Could not load libtorchcodec". Si pasa eso,
    precargamos el audio con torchaudio (backend soundfile, no depende de
    FFmpeg/torchcodec para WAV) y se lo pasamos al pipeline como waveform,
    formato que pyannote soporta desde siempre y que evita el decoder de
    torchcodec por completo. Cualquier otro error se relanza tal cual.
    """
    try:
        return pipeline(str(audio_path))
    except Exception as exc:
        if "torchcodec" not in str(exc).lower():
            raise

        import torchaudio

        waveform, sample_rate = torchaudio.load(str(audio_path))
        return pipeline({"waveform": waveform, "sample_rate": sample_rate})


def diarize_audio(
    audio_path: Path,
    *,
    model: str = DEFAULT_MODEL,
    hf_token: str | None = None,
    device: str = DEFAULT_DEVICE,
) -> list[SpeakerTurn]:
    """Corre pyannote sobre `audio_path` y devuelve sus turnos de hablante.

    `hf_token` por defecto viene de la variable de entorno HF_TOKEN. Lanza
    FileNotFoundError si `audio_path` no existe, y DiarizationError si falta
    el token, si pyannote.audio no esta instalado, o si el pipeline falla
    (incluye el 401/403 de un modelo "gated" sin licencia aceptada).
    """
    if not audio_path.exists():
        raise FileNotFoundError(f"No existe el archivo de audio: {audio_path}")

    token = hf_token or os.environ.get("HF_TOKEN")
    if not token:
        raise DiarizationError(
            "Falta HF_TOKEN. pyannote.audio necesita un token de Hugging Face con "
            "acceso a los modelos 'gated' de diarizacion (ver docs/estado-proyecto.md: "
            "aceptar la licencia en huggingface.co/pyannote/speaker-diarization-3.1 y "
            "pyannote/segmentation-3.0, y generar un token 'read' en "
            "huggingface.co/settings/tokens). Definilo como variable de entorno HF_TOKEN "
            "(o pasa hf_token explicitamente)."
        )

    try:
        from pyannote.audio import Pipeline
    except ImportError as exc:
        raise DiarizationError(
            "Falta el paquete 'pyannote.audio'. Instala con: uv sync --extra diarization"
        ) from exc

    try:
        pipeline = _load_pipeline(Pipeline, model, token)
        if device != "cpu":
            import torch

            pipeline.to(torch.device(device))
        diarization = _run_pipeline(pipeline, audio_path)
    except Exception as exc:
        raise DiarizationError(
            f"Fallo diarizando {audio_path} con el modelo '{model}': {exc}. Si es un "
            "401/403, revisa que hayas aceptado la licencia del modelo en huggingface.co "
            "y que el HF_TOKEN tenga acceso (ver docs/estado-proyecto.md)."
        ) from exc

    return [
        SpeakerTurn(start=turn.start, end=turn.end, speaker=speaker)
        for turn, _, speaker in diarization.itertracks(yield_label=True)
    ]
