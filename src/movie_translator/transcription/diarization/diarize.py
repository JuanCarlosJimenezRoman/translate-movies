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


def _load_wav_without_torchcodec(audio_path: Path):
    """Carga un WAV a un tensor `(channel, time)` float32 sin ffmpeg/torchcodec.

    Usa `scipy.io.wavfile` (parser de WAV propio de scipy, sin dependencias
    externas de ffmpeg) en vez de `torchaudio.load()` -- en las versiones
    recientes de torchaudio, `load()` tambien delega en torchcodec para leer
    el archivo, asi que no sirve como fallback (falla con el mismo error).
    Solo soporta WAV, que es lo unico que esta etapa le pasa (el .wav que
    genera `run_extraction`).
    """
    import numpy as np
    import torch
    from scipy.io import wavfile

    sample_rate, data = wavfile.read(str(audio_path))
    if data.ndim == 1:
        data = data[:, None]  # (samples,) -> (samples, 1 canal)

    if np.issubdtype(data.dtype, np.integer):
        max_value = float(np.iinfo(data.dtype).max)
        data = data.astype(np.float32) / max_value
    else:
        data = data.astype(np.float32)

    waveform = torch.from_numpy(data.T.copy())  # (channel, time)
    return waveform, sample_rate


def _run_pipeline(pipeline: object, audio_path: Path):
    """Corre `pipeline` sobre `audio_path`, con fallback si falta torchcodec.

    pyannote.audio 4.0+ lee el audio con torchcodec (ver el docstring de
    este modulo en pyannote: "relies on torchcodec for reading"), y
    torchcodec necesita una build de FFmpeg "full-shared" (con DLLs) que
    muchas instalaciones de Windows no tienen -- falla con "Could not load
    libtorchcodec".

    Si el pipeline falla por torchcodec, precargamos el WAV nosotros mismos
    (`_load_wav_without_torchcodec`) y se lo pasamos al pipeline como
    `{"waveform": tensor, "sample_rate": sr}` -- el formato "audio
    precargado en memoria" que el propio pyannote.audio documenta como
    alternativa cuando torchcodec no esta disponible: tanto `Audio.__call__`
    como `Audio.crop()` (usado para extraer cada segmento de hablante) usan
    ese tensor directamente y nunca tocan `AudioDecoder`/torchcodec cuando
    "waveform" ya viene en el dict. Cualquier otro error se relanza tal
    cual.
    """
    try:
        return pipeline(str(audio_path))
    except Exception as exc:
        if "torchcodec" not in str(exc).lower():
            raise

        waveform, sample_rate = _load_wav_without_torchcodec(audio_path)
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

    # pyannote.audio 4.0+ devuelve un `DiarizeOutput` (dataclass con
    # `.speaker_diarization`, `.exclusive_speaker_diarization`,
    # `.speaker_embeddings`) en vez de la `Annotation` que devolvia
    # directamente en versiones anteriores (`pyproject.toml` fija
    # `pyannote.audio>=3.3`, sin techo). `getattr` con default cubre ambas:
    # si no tiene `speaker_diarization` es porque ya es la Annotation vieja.
    annotation = getattr(diarization, "speaker_diarization", diarization)

    return [
        SpeakerTurn(start=turn.start, end=turn.end, speaker=speaker)
        for turn, _, speaker in annotation.itertracks(yield_label=True)
    ]
