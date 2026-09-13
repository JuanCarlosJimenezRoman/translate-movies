"""Inspeccion de archivos de video/audio via ffprobe, sin decodificarlos."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from movie_translator.media.ffmpeg.errors import FFmpegError, FFmpegNotFoundError


def require_binary(name: str) -> str:
    """Resuelve el binario `name` en el PATH o lanza FFmpegNotFoundError."""
    path = shutil.which(name)
    if path is None:
        raise FFmpegNotFoundError(
            f"'{name}' no esta instalado o no esta en el PATH. "
            "Instalalo (por ejemplo 'apt install ffmpeg') antes de continuar."
        )
    return path


@dataclass(frozen=True)
class MediaInfo:
    """Metadata minima de un archivo de video/audio."""

    duration_seconds: float
    has_audio: bool
    has_video: bool
    audio_sample_rate: int | None
    audio_channels: int | None


def probe(path: Path) -> MediaInfo:
    """Inspecciona `path` con ffprobe y devuelve su metadata basica.

    Lanza FileNotFoundError si el archivo no existe, FFmpegNotFoundError si
    ffprobe no esta instalado, y FFmpegError si ffprobe falla (archivo
    corrupto o formato no reconocido).
    """
    ffprobe = require_binary("ffprobe")
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo: {path}")

    result = subprocess.run(
        [
            ffprobe,
            "-v", "error",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise FFmpegError(f"ffprobe fallo inspeccionando {path}", result.stderr)

    data = json.loads(result.stdout)
    streams = data.get("streams", [])
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
    video_streams = [s for s in streams if s.get("codec_type") == "video"]

    duration = float(data.get("format", {}).get("duration", 0.0))
    audio_sample_rate = (
        int(audio_streams[0]["sample_rate"])
        if audio_streams and "sample_rate" in audio_streams[0]
        else None
    )
    audio_channels = (
        int(audio_streams[0]["channels"])
        if audio_streams and "channels" in audio_streams[0]
        else None
    )

    return MediaInfo(
        duration_seconds=duration,
        has_audio=bool(audio_streams),
        has_video=bool(video_streams),
        audio_sample_rate=audio_sample_rate,
        audio_channels=audio_channels,
    )
