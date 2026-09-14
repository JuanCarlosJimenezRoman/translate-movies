"""Tests de core/pipeline/diarization.py (run_diarization), mockeando
diarize_audio para no depender de pyannote.audio ni de un HF_TOKEN real."""

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
from movie_translator.core.pipeline import TRANSCRIPT_FILENAME, run_diarization
from movie_translator.core.pipeline.extraction import ORIGINAL_AUDIO_FILENAME
from movie_translator.transcription.diarization import (
    DiarizationError,
    SpeakerInfo,
    SpeakerTurn,
    load_speakers,
    save_speakers,
)

_ORIGINAL_SEGMENTS = [
    Segment(start=0.0, end=1.0, text="hello"),
    Segment(start=1.0, end=2.0, text="world"),
]

_FAKE_TURNS = [
    SpeakerTurn(start=0.0, end=1.0, speaker="SPEAKER_00"),
    SpeakerTurn(start=1.0, end=2.0, speaker="SPEAKER_01"),
]


def _project_with_transcript(tmp_path: Path, name: str = "matrix"):
    project, paths = create_project(
        tmp_path / "projects", name, source_language="en", target_language="es"
    )
    (paths.audio / ORIGINAL_AUDIO_FILENAME).write_bytes(b"fake wav")
    from movie_translator.core.models.segment import save_segments

    save_segments(_ORIGINAL_SEGMENTS, paths.transcription / TRANSCRIPT_FILENAME)
    return project, paths


def test_run_diarization_completes_and_assigns_speakers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "movie_translator.core.pipeline.diarization.diarize_audio",
        lambda *args, **kwargs: _FAKE_TURNS,
    )
    project, paths = _project_with_transcript(tmp_path)

    run_diarization(project, paths, hf_token="fake-token")

    assert project.stages[StageName.DIARIZATION] == StageStatus.COMPLETED

    segments = load_segments(paths.transcription / TRANSCRIPT_FILENAME)
    assert [s.speaker for s in segments] == ["SPEAKER_00", "SPEAKER_01"]

    reloaded = Project.load(paths.project_json)
    assert reloaded.stages[StageName.DIARIZATION] == StageStatus.COMPLETED


def test_run_diarization_creates_speakers_json_placeholders(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "movie_translator.core.pipeline.diarization.diarize_audio",
        lambda *args, **kwargs: _FAKE_TURNS,
    )
    project, paths = _project_with_transcript(tmp_path)

    run_diarization(project, paths, hf_token="fake-token")

    speakers = load_speakers(paths.speakers_json)
    assert set(speakers) == {"SPEAKER_00", "SPEAKER_01"}
    assert all(info.character is None for info in speakers.values())


def test_run_diarization_does_not_overwrite_named_speakers(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Si 'name-speakers' ya nombro a un hablante, re-correr diarizacion no lo pisa."""
    monkeypatch.setattr(
        "movie_translator.core.pipeline.diarization.diarize_audio",
        lambda *args, **kwargs: _FAKE_TURNS,
    )
    project, paths = _project_with_transcript(tmp_path)
    save_speakers({"SPEAKER_00": SpeakerInfo(character="Neo")}, paths.speakers_json)

    run_diarization(project, paths, hf_token="fake-token")

    speakers = load_speakers(paths.speakers_json)
    assert speakers["SPEAKER_00"].character == "Neo"
    assert speakers["SPEAKER_01"].character is None


def test_run_diarization_requires_transcription(tmp_path: Path) -> None:
    project, paths = create_project(
        tmp_path / "projects", "sintranscribir", source_language="en", target_language="es"
    )

    with pytest.raises(FileNotFoundError):
        run_diarization(project, paths, hf_token="fake-token")

    assert project.stages[StageName.DIARIZATION] == StageStatus.PENDING


def test_run_diarization_marks_failed_on_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def fake_diarize(*args, **kwargs):
        raise DiarizationError("boom")

    monkeypatch.setattr("movie_translator.core.pipeline.diarization.diarize_audio", fake_diarize)
    project, paths = _project_with_transcript(tmp_path)

    with pytest.raises(DiarizationError):
        run_diarization(project, paths, hf_token="fake-token")

    assert project.stages[StageName.DIARIZATION] == StageStatus.FAILED

    reloaded = Project.load(paths.project_json)
    assert reloaded.stages[StageName.DIARIZATION] == StageStatus.FAILED
