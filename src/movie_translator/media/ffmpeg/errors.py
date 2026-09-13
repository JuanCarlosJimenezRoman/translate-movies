"""Errores especificos de las operaciones con FFmpeg/ffprobe."""

from __future__ import annotations


class FFmpegNotFoundError(RuntimeError):
    """FFmpeg (o ffprobe) no esta instalado o no esta en el PATH."""


class FFmpegError(RuntimeError):
    """FFmpeg (o ffprobe) devolvio un codigo de salida distinto de cero."""

    def __init__(self, message: str, stderr: str = "") -> None:
        super().__init__(message)
        self.stderr = stderr
