"""Tests de transcription/whisper/transcribe.py, con faster-whisper mockeado.

No se descarga ningun modelo real: instanciar WhisperModel de verdad
implicaria red y minutos de espera, algo que no debe depender un test
unitario. Se verifica solo la logica propia (conversion a Segment, manejo
de errores), no faster-whisper en si.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import ClassVar

import pytest

from movie_translator.transcription.whisper import (
    DEFAULT_VAD_PARAMETERS,
    TranscriptionError,
    transcribe_audio,
)


@dataclass
class _FakeWhisperSegment:
    start: float
    end: float
    text: str
    avg_logprob: float


class _FakeWhisperModel:
    """Reemplaza a faster_whisper.WhisperModel en los tests."""

    last_init_kwargs: ClassVar[dict | None] = None
    last_transcribe_kwargs: ClassVar[dict | None] = None
    segments: ClassVar[list[_FakeWhisperSegment]] = [
        _FakeWhisperSegment(0.0, 1.5, "  Hello there.  ", avg_logprob=-0.1),
        _FakeWhisperSegment(1.5, 3.2, "General Kenobi.", avg_logprob=-0.5),
    ]

    def __init__(self, model_size: str, **kwargs: object) -> None:
        _FakeWhisperModel.last_init_kwargs = {"model_size": model_size, **kwargs}

    def transcribe(self, audio_path: str, **kwargs: object):
        _FakeWhisperModel.last_transcribe_kwargs = {"audio_path": audio_path, **kwargs}
        return iter(self.segments), SimpleNamespace(language="en")


class _RaisingWhisperModel:
    def __init__(self, *args: object, **kwargs: object) -> None:
        raise RuntimeError("no se pudo cargar el modelo (simulado)")


def test_transcribe_audio_converts_segments(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "movie_translator.transcription.whisper.transcribe.WhisperModel", _FakeWhisperModel
    )
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"fake wav")

    segments = transcribe_audio(audio, model_size="tiny", language="en")

    assert len(segments) == 2
    assert segments[0].text == "Hello there."  # se hace .strip()
    assert segments[0].start == 0.0
    assert segments[0].end == 1.5
    assert 0.0 <= segments[0].confidence <= 1.0
    assert segments[1].text == "General Kenobi."


def test_transcribe_audio_passes_language_and_model_size(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "movie_translator.transcription.whisper.transcribe.WhisperModel", _FakeWhisperModel
    )
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"fake wav")

    transcribe_audio(audio, model_size="small", language="es")

    assert _FakeWhisperModel.last_init_kwargs["model_size"] == "small"
    assert _FakeWhisperModel.last_transcribe_kwargs["language"] == "es"


def test_transcribe_audio_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        transcribe_audio(tmp_path / "no_existe.wav")


def test_transcribe_audio_uses_permissive_vad_by_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """El VAD por defecto debe ser mas permisivo que el de faster-whisper
    (threshold=0.5) para no descartar canciones enteras -- ver el comentario
    junto a DEFAULT_VAD_PARAMETERS en transcribe.py."""
    monkeypatch.setattr(
        "movie_translator.transcription.whisper.transcribe.WhisperModel", _FakeWhisperModel
    )
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"fake wav")

    transcribe_audio(audio)

    kwargs = _FakeWhisperModel.last_transcribe_kwargs
    assert kwargs["vad_filter"] is True
    assert kwargs["vad_parameters"] == DEFAULT_VAD_PARAMETERS
    assert kwargs["vad_parameters"]["threshold"] < 0.5


def test_transcribe_audio_allows_overriding_vad_parameters(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "movie_translator.transcription.whisper.transcribe.WhisperModel", _FakeWhisperModel
    )
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"fake wav")
    custom = {"threshold": 0.5, "min_silence_duration_ms": 2000, "speech_pad_ms": 400}

    transcribe_audio(audio, vad_parameters=custom)

    assert _FakeWhisperModel.last_transcribe_kwargs["vad_parameters"] == custom


def test_transcribe_audio_wraps_model_errors(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "movie_translator.transcription.whisper.transcribe.WhisperModel", _RaisingWhisperModel
    )
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"fake wav")

    with pytest.raises(TranscriptionError, match="no se pudo cargar el modelo"):
        transcribe_audio(audio)
