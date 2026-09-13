"""Tests de src/movie_translator/core/models (Segment, Project, project.json)."""

from __future__ import annotations

from pathlib import Path

import pytest

from movie_translator.core.models import (
    STAGE_ORDER,
    Project,
    Segment,
    StageName,
    StageStatus,
    create_project,
    load_project,
)

# -- Segment ------------------------------------------------------------------


def test_segment_duration() -> None:
    segment = Segment(start=12.42, end=15.87, text="We need to get out of here.")

    assert segment.duration == pytest.approx(3.45)
    assert segment.speaker is None
    assert segment.confidence is None


def test_segment_rejects_end_before_start() -> None:
    with pytest.raises(ValueError, match="no puede ser menor"):
        Segment(start=10.0, end=5.0, text="x")


def test_segment_rejects_negative_start() -> None:
    with pytest.raises(ValueError):
        Segment(start=-1.0, end=1.0, text="x")


def test_segment_confidence_must_be_a_fraction() -> None:
    with pytest.raises(ValueError):
        Segment(start=0.0, end=1.0, text="x", confidence=1.5)


# -- Project: estado y progreso ------------------------------------------------


def test_new_project_starts_with_all_stages_pending() -> None:
    project = Project(name="matrix", source_language="en", target_language="es")

    assert set(project.stages) == set(STAGE_ORDER)
    assert all(status == StageStatus.PENDING for status in project.stages.values())
    assert project.pending_stage() == StageName.EXTRACTION


def test_mark_stage_updates_status_and_timestamp() -> None:
    project = Project(name="matrix", source_language="en", target_language="es")
    before = project.updated_at

    project.mark_stage(StageName.EXTRACTION, StageStatus.COMPLETED)

    assert project.stages[StageName.EXTRACTION] == StageStatus.COMPLETED
    assert project.updated_at >= before
    assert project.pending_stage() == StageName.SEPARATION


def test_pending_stage_is_none_when_all_completed() -> None:
    project = Project(name="matrix", source_language="en", target_language="es")
    for stage in STAGE_ORDER:
        project.mark_stage(stage, StageStatus.COMPLETED)

    assert project.pending_stage() is None


def test_progress_lines_reflect_stage_status() -> None:
    project = Project(name="matrix", source_language="en", target_language="es")
    project.mark_stage(StageName.EXTRACTION, StageStatus.COMPLETED)
    project.mark_stage(StageName.SEPARATION, StageStatus.RUNNING)

    lines = project.progress_lines()

    assert lines[0] == "✓ extraction"
    assert lines[1] == "→ separation"
    assert lines[2] == "○ transcription"


# -- Project: persistencia en project.json -------------------------------------


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    project = Project(name="matrix", source_language="en", target_language="es")
    project.mark_stage(StageName.EXTRACTION, StageStatus.COMPLETED)
    path = tmp_path / "project.json"

    project.save(path)
    loaded = Project.load(path)

    assert loaded == project
    assert loaded.stages[StageName.EXTRACTION] == StageStatus.COMPLETED


def test_load_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        Project.load(tmp_path / "no_existe.json")


# -- create_project / load_project (layout de projects/<name>/) ---------------


def test_create_project_creates_expected_layout(tmp_path: Path) -> None:
    project, paths = create_project(
        tmp_path, "matrix", source_language="en", target_language="es"
    )

    assert project.name == "matrix"
    assert paths.root == tmp_path / "matrix"
    for sub in ("source", "audio", "transcription", "translation", "voices", "subtitles", "output"):
        assert (paths.root / sub).is_dir()
    assert paths.project_json.exists()


def test_create_project_rejects_invalid_name(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        create_project(tmp_path, "Matrix Reloaded!", source_language="en", target_language="es")


def test_create_project_refuses_to_overwrite_existing(tmp_path: Path) -> None:
    create_project(tmp_path, "matrix", source_language="en", target_language="es")

    with pytest.raises(FileExistsError):
        create_project(tmp_path, "matrix", source_language="en", target_language="es")


def test_load_project_roundtrips_through_create(tmp_path: Path) -> None:
    created, _ = create_project(tmp_path, "matrix", source_language="en", target_language="es")

    loaded, paths = load_project(tmp_path, "matrix")

    assert loaded == created
    assert paths.root == tmp_path / "matrix"


def test_load_project_missing_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_project(tmp_path, "no_existe")
