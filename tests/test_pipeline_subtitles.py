"""Tests de core/pipeline/subtitles.py (run_subtitles)."""

from __future__ import annotations

from pathlib import Path

import pytest
import srt as srt_lib

from movie_translator.core.models import Project, Segment, StageName, StageStatus, create_project
from movie_translator.core.models.segment import save_segments
from movie_translator.core.pipeline import TRANSLATED_FILENAME, run_subtitles


def _project_with_translation(tmp_path: Path, name: str = "matrix"):
    project, paths = create_project(
        tmp_path / "projects", name, source_language="en", target_language="es"
    )
    segments = [
        Segment(start=0.0, end=2.0, text="hola mundo"),
        Segment(start=2.0, end=4.0, text="como estas"),
    ]
    save_segments(segments, paths.translation / TRANSLATED_FILENAME)
    return project, paths


def test_run_subtitles_completes_and_writes_srt(tmp_path: Path) -> None:
    project, paths = _project_with_translation(tmp_path)

    project, warnings = run_subtitles(project, paths)

    assert project.stages[StageName.SUBTITLES] == StageStatus.COMPLETED
    assert warnings == []

    srt_path = paths.subtitles / "es.srt"
    assert srt_path.exists()
    parsed = list(srt_lib.parse(srt_path.read_text(encoding="utf-8")))
    assert [cue.content for cue in parsed] == ["hola mundo", "como estas"]

    reloaded = Project.load(paths.project_json)
    assert reloaded.stages[StageName.SUBTITLES] == StageStatus.COMPLETED


def test_run_subtitles_names_file_by_target_language(tmp_path: Path) -> None:
    project, paths = create_project(
        tmp_path / "projects", "pelicula", source_language="en", target_language="fr"
    )
    save_segments(
        [Segment(start=0.0, end=1.0, text="bonjour")],
        paths.translation / TRANSLATED_FILENAME,
    )

    run_subtitles(project, paths)

    assert (paths.subtitles / "fr.srt").exists()


def test_run_subtitles_requires_translation(tmp_path: Path) -> None:
    project, paths = create_project(
        tmp_path / "projects", "sintraducir", source_language="en", target_language="es"
    )

    with pytest.raises(FileNotFoundError):
        run_subtitles(project, paths)

    assert project.stages[StageName.SUBTITLES] == StageStatus.PENDING


def test_run_subtitles_surfaces_readability_warnings(tmp_path: Path) -> None:
    project, paths = create_project(
        tmp_path / "projects", "conwarnings", source_language="en", target_language="es"
    )
    long_text = " ".join(["palabra"] * 30)
    save_segments(
        [Segment(start=0.0, end=1.0, text=long_text)],
        paths.translation / TRANSLATED_FILENAME,
    )

    _, warnings = run_subtitles(project, paths)

    assert len(warnings) >= 1
    assert project.stages[StageName.SUBTITLES] == StageStatus.COMPLETED  # se genera igual
