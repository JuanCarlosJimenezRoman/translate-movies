"""Wrappers sobre el binario de FFmpeg/ffprobe."""

from movie_translator.media.ffmpeg.errors import FFmpegError, FFmpegNotFoundError
from movie_translator.media.ffmpeg.extract import (
    WHISPER_CHANNELS,
    WHISPER_SAMPLE_RATE,
    extract_audio,
)
from movie_translator.media.ffmpeg.probe import MediaInfo, probe

__all__ = [
    "WHISPER_CHANNELS",
    "WHISPER_SAMPLE_RATE",
    "FFmpegError",
    "FFmpegNotFoundError",
    "MediaInfo",
    "extract_audio",
    "probe",
]
