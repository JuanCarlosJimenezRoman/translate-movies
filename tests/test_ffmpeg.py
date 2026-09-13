"""Tests de src/movie_translator/media/ffmpeg (extraccion de audio)."""

from __future__ import annotations

import wave
from pathlib import Path

import pytest

from movie_translator.media.ffmpeg import (
    FFmpegError,
    extract_audio,
    probe,
)


def test_probe_detects_audio_and_video(sample_video_with_audio: Path) -> None:
    info = probe(sample_video_with_audio)

    assert info.has_audio is True
    assert info.has_video is True
    assert info.duration_seconds == pytest.approx(2.0, abs=0.3)


def test_probe_detects_missing_audio(sample_video_without_audio: Path) -> None:
    info = probe(sample_video_without_audio)

    assert info.has_audio is False
    assert info.has_video is True


def test_probe_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        probe(tmp_path / "no_existe.mp4")


def test_extract_audio_produces_16k_mono_wav(
    sample_video_with_audio: Path, tmp_path: Path
) -> None:
    out = tmp_path / "out.wav"

    result = extract_audio(sample_video_with_audio, out)

    assert result == out
    assert out.exists()

    with wave.open(str(out), "rb") as wav_file:
        assert wav_file.getframerate() == 16000
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2  # pcm_s16le = 16 bits = 2 bytes
        assert wav_file.getnframes() > 0


def test_extract_audio_missing_video_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        extract_audio(tmp_path / "no_existe.mp4", tmp_path / "out.wav")


def test_extract_audio_without_audio_track_raises(
    sample_video_without_audio: Path, tmp_path: Path
) -> None:
    with pytest.raises(FFmpegError):
        extract_audio(sample_video_without_audio, tmp_path / "out.wav")


def test_extract_audio_refuses_overwrite_by_default(
    sample_video_with_audio: Path, tmp_path: Path
) -> None:
    out = tmp_path / "out.wav"
    out.write_bytes(b"ya existe")

    with pytest.raises(FileExistsError):
        extract_audio(sample_video_with_audio, out)


def test_extract_audio_overwrite_true_replaces_file(
    sample_video_with_audio: Path, tmp_path: Path
) -> None:
    out = tmp_path / "out.wav"
    out.write_bytes(b"contenido viejo")

    extract_audio(sample_video_with_audio, out, overwrite=True)

    assert out.stat().st_size > len(b"contenido viejo")
