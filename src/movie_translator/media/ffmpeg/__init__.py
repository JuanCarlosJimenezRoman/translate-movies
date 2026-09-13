"""Wrappers sobre el binario de FFmpeg/ffprobe."""

from movie_translator.media.ffmpeg.errors import FFmpegError, FFmpegNotFoundError
from movie_translator.media.ffmpeg.extract import (
    WHISPER_CHANNELS,
    WHISPER_SAMPLE_RATE,
    extract_audio,
)
from movie_translator.media.ffmpeg.probe import MediaInfo, probe

__all__ = [
    "FFmpegError",
    "FFmpegNotFoundError",
    "MediaInfo",
    "probe",
    "extract_audio",
    "WHISPER_SAMPLE_RATE",
    "WHISPER_CHANNELS",
]
