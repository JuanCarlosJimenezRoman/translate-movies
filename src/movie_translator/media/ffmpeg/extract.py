"""Extraccion de la pista de audio de un video, via FFmpeg.

FFmpeg se invoca como subproceso (binario del sistema) en vez de usar un
wrapper de Python: es mas simple, no agrega una dependencia mas, y expone
directamente los mismos flags que la documentacion oficial de FFmpeg.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from movie_translator.media.ffmpeg.errors import FFmpegError
from movie_translator.media.ffmpeg.probe import probe, require_binary

# faster-whisper (y la mayoria de modelos de ASR) esperan PCM mono a 16kHz.
WHISPER_SAMPLE_RATE = 16000
WHISPER_CHANNELS = 1


def extract_audio(
    video_path: Path,
    output_path: Path,
    *,
    sample_rate: int = WHISPER_SAMPLE_RATE,
    channels: int = WHISPER_CHANNELS,
    overwrite: bool = False,
) -> Path:
    """Extrae el audio de `video_path` como WAV PCM 16-bit en `output_path`.

    Por defecto usa 16kHz mono: el formato que espera faster-whisper (Fase 1).

    Lanza:
      - FileNotFoundError si `video_path` no existe.
      - FileExistsError si `output_path` ya existe y `overwrite=False`.
      - FFmpegNotFoundError si ffmpeg/ffprobe no estan en el PATH.
      - FFmpegError si el video no tiene pista de audio, o si ffmpeg falla.
    """
    ffmpeg = require_binary("ffmpeg")

    if not video_path.exists():
        raise FileNotFoundError(f"No existe el archivo de video: {video_path}")

    if output_path.exists() and not overwrite:
        raise FileExistsError(
            f"{output_path} ya existe. Usa overwrite=True para sobreescribirlo."
        )

    info = probe(video_path)
    if not info.has_audio:
        raise FFmpegError(f"{video_path} no tiene ninguna pista de audio")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        ffmpeg,
        "-y",  # ya validamos overwrite arriba; siempre sobreescribimos aqui
        "-i", str(video_path),
        "-vn",  # descartar video
        "-acodec", "pcm_s16le",
        "-ar", str(sample_rate),
        "-ac", str(channels),
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise FFmpegError(
            f"ffmpeg fallo extrayendo audio de {video_path}", result.stderr
        )

    return output_path
