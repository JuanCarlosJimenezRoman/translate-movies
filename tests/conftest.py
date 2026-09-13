"""Fixtures compartidas para tests. Generan clips sinteticos con FFmpeg
(lavfi) en vez de guardar binarios de video en el repo."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


def _ffmpeg() -> str:
    path = shutil.which("ffmpeg")
    if path is None:
        pytest.skip("ffmpeg no esta instalado en este entorno")
    return path


@pytest.fixture()
def sample_video_with_audio(tmp_path: Path) -> Path:
    """Video sintetico de 2s (color + tono) con pista de audio."""
    out = tmp_path / "sample_with_audio.mp4"
    subprocess.run(
        [
            _ffmpeg(), "-y",
            "-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=10",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
            "-c:v", "libx264", "-c:a", "aac",
            "-shortest",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return out


@pytest.fixture()
def sample_video_without_audio(tmp_path: Path) -> Path:
    """Video sintetico de 1s sin ninguna pista de audio."""
    out = tmp_path / "sample_without_audio.mp4"
    subprocess.run(
        [
            _ffmpeg(), "-y",
            "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=10",
            "-c:v", "libx264",
            "-an",
            str(out),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return out
