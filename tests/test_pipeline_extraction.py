"""Tests de core/pipeline/extraction.py (run_extraction)."""

from __future__ import annotations

from pathlib import Path

import pytest

from movie_translator.core.models import StageName, StageStatus, create_project
from movie_translator.core.pipeline import ORIGINAL_AUDIO_FILENAME, run_extraction
from movie_translator.media.ffmpeg import FFmpegError


def test_run_extraction_completes_and_updates_project(
    sample_video_with_audio: Path, tmp_path: Path
) -> None:
    project, paths = create_project(
        tmp_path / "projects", "matrix", source_language="en", target_language="es"
    )

    result = run_extraction(project, paths, sample_video_with_audio)

    assert result is project
    assert project.stages[StageName.EXTRACTION] == StageStatus.COMPLETED
    assert project.source_file == str(sample_video_with_audio.resolve())
    assert project.duration_seconds == pytest.approx(2.0, abs=0.3)

    audio_file = paths.audio / ORIGINAL_AUDIO_FILENAME
    assert audio_file.exists()

    # el estado quedo persistido en disco, no solo en el objeto en memoria
    from movie_translator.core.models import Project

    reloaded = Project.load(paths.project_json)
    assert reloaded.stages[StageName.EXTRACTION] == StageStatus.COMPLETED
    assert reloaded.duration_seconds == project.duration_seconds


def test_run_extraction_marks_failed_on_video_without_audio(
    sample_video_without_audio: Path, tmp_path: Path
) -> None:
    project, paths = create_project(
        tmp_path / "projects", "sinaudio", source_language="en", target_language="es"
    )

    with pytest.raises(FFmpegError):
        run_extraction(project, paths, sample_video_without_audio)

    assert project.stages[StageName.EXTRACTION] == StageStatus.FAILED

    from movie_translator.core.models import Project

    reloaded = Project.load(paths.project_json)
    assert reloaded.stages[StageName.EXTRACTION] == StageStatus.FAILED


def test_run_extraction_missing_video_raises_and_does_not_touch_project(
    tmp_path: Path,
) -> None:
    project, paths = create_project(
        tmp_path / "projects", "noexiste", source_language="en", target_language="es"
    )
    before = project.stages[StageName.EXTRACTION]

    with pytest.raises(FileNotFoundError):
        run_extraction(project, paths, tmp_path / "no_existe.mp4")

    # el video ni siquiera se resolvio: la etapa no llega a marcarse "running"
    assert project.stages[StageName.EXTRACTION] == before
