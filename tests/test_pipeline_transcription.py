"""Tests de core/pipeline/transcription.py (run_transcription), mockeando
transcribe_audio para no depender de un modelo real de Whisper."""

from __future__ import annotations

from pathlib import Path

import pytest

from movie_translator.core.models import (
    Project,
    Segment,
    StageName,
    StageStatus,
    create_project,
    load_segments,
)
from movie_translator.core.pipeline import TRANSCRIPT_FILENAME, run_transcription
from movie_translator.core.pipeline.extraction import ORIGINAL_AUDIO_FILENAME
from movie_translator.transcription.whisper import TranscriptionError

_FAKE_SEGMENTS = [
    Segment(start=0.0, end=1.0, text="hola", confidence=0.9),
    Segment(start=1.0, end=2.0, text="mundo", confidence=0.8),
]


def _project_with_audio(tmp_path: Path, name: str = "matrix"):
    project, paths = create_project(
        tmp_path / "projects", name, source_language="en", target_language="es"
    )
    (paths.audio / ORIGINAL_AUDIO_FILENAME).write_bytes(b"fake wav")
    return project, paths


def test_run_transcription_completes_and_saves_segments(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "movie_translator.core.pipeline.transcription.transcribe_audio",
        lambda *args, **kwargs: _FAKE_SEGMENTS,
    )
    project, paths = _project_with_audio(tmp_path)

    run_transcription(project, paths)

    assert project.stages[StageName.TRANSCRIPTION] == StageStatus.COMPLETED

    saved = load_segments(paths.transcription / TRANSCRIPT_FILENAME)
    assert saved == _FAKE_SEGMENTS

    reloaded = Project.load(paths.project_json)
    assert reloaded.stages[StageName.TRANSCRIPTION] == StageStatus.COMPLETED


def test_run_transcription_passes_source_language(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    captured: dict = {}

    def fake_transcribe(audio_path, *, model_size, language, models_dir):
        captured["language"] = language
        captured["model_size"] = model_size
        return _FAKE_SEGMENTS

    monkeypatch.setattr(
        "movie_translator.core.pipeline.transcription.transcribe_audio", fake_transcribe
    )
    project, paths = _project_with_audio(tmp_path)
    project.source_language = "fr"

    run_transcription(project, paths, model_size="tiny")

    assert captured["language"] == "fr"
    assert captured["model_size"] == "tiny"


def test_run_transcription_requires_extracted_audio(tmp_path: Path) -> None:
    project, paths = create_project(
        tmp_path / "projects", "sinaudio", source_language="en", target_language="es"
    )

    with pytest.raises(FileNotFoundError):
        run_transcription(project, paths)

    assert project.stages[StageName.TRANSCRIPTION] == StageStatus.PENDING


def test_run_transcription_marks_failed_on_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_transcribe(*args, **kwargs):
        raise TranscriptionError("boom")

    monkeypatch.setattr(
        "movie_translator.core.pipeline.transcription.transcribe_audio", fake_transcribe
    )
    project, paths = _project_with_audio(tmp_path)

    with pytest.raises(TranscriptionError):
        run_transcription(project, paths)

    assert project.stages[StageName.TRANSCRIPTION] == StageStatus.FAILED

    reloaded = Project.load(paths.project_json)
    assert reloaded.stages[StageName.TRANSCRIPTION] == StageStatus.FAILED
