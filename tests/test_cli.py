"""Tests de extremo a extremo del CLI (apps/cli/main.py) via CliRunner."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

import apps.cli.main as cli_main
from apps.cli.main import app
from movie_translator.core.models import Segment

runner = CliRunner()

_FAKE_SEGMENTS = [Segment(start=0.0, end=1.0, text="hola", confidence=0.9)]


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert "movie-translator" in result.stdout


def test_new_then_analyze_end_to_end(sample_video_with_audio: Path, tmp_path: Path) -> None:
    projects_root = tmp_path / "projects"

    new_result = runner.invoke(
        app,
        [
            "new",
            str(sample_video_with_audio),
            "--name", "demo",
            "--projects-root", str(projects_root),
        ],
    )
    assert new_result.exit_code == 0, new_result.stdout
    assert "creado" in new_result.stdout
    assert "Audio extraido correctamente" in new_result.stdout
    assert "✓ extraction" in new_result.stdout

    analyze_result = runner.invoke(
        app, ["analyze", "demo", "--projects-root", str(projects_root)]
    )
    assert analyze_result.exit_code == 0, analyze_result.stdout
    assert "demo" in analyze_result.stdout
    assert "en -> es" in analyze_result.stdout
    assert "✓ extraction" in analyze_result.stdout

    assert (projects_root / "demo" / "audio" / "original.wav").exists()


def test_new_rejects_missing_video(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "new",
            str(tmp_path / "no_existe.mp4"),
            "--projects-root", str(tmp_path / "projects"),
        ],
    )

    assert result.exit_code == 1
    assert "no existe" in result.stdout.lower()


def test_new_rejects_duplicate_project(sample_video_with_audio: Path, tmp_path: Path) -> None:
    projects_root = tmp_path / "projects"
    args = [
        "new",
        str(sample_video_with_audio),
        "--name", "demo",
        "--projects-root", str(projects_root),
    ]

    first = runner.invoke(app, args)
    assert first.exit_code == 0, first.stdout

    second = runner.invoke(app, args)
    assert second.exit_code == 1
    assert "ya existe" in second.stdout


def test_analyze_missing_project_reports_error(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["analyze", "no_existe", "--projects-root", str(tmp_path / "projects")]
    )

    assert result.exit_code == 1
    assert "Error" in result.stdout


def test_new_derives_name_from_filename(sample_video_with_audio: Path, tmp_path: Path) -> None:
    # sample_video_with_audio se llama "sample_with_audio.mp4" (ver conftest.py)
    projects_root = tmp_path / "projects"

    result = runner.invoke(
        app,
        ["new", str(sample_video_with_audio), "--projects-root", str(projects_root)],
    )

    assert result.exit_code == 0, result.stdout
    assert (projects_root / "sample_with_audio").is_dir()


def test_transcribe_command_end_to_end(
    monkeypatch: pytest.MonkeyPatch, sample_video_with_audio: Path, tmp_path: Path
) -> None:
    projects_root = tmp_path / "projects"
    monkeypatch.setattr(
        cli_main, "run_transcription", lambda project, paths, **kw: project
    )

    new_result = runner.invoke(
        app,
        ["new", str(sample_video_with_audio), "--name", "demo", "--projects-root", str(projects_root)],
    )
    assert new_result.exit_code == 0, new_result.stdout

    transcribe_result = runner.invoke(
        app, ["transcribe", "demo", "--projects-root", str(projects_root)]
    )

    assert transcribe_result.exit_code == 0, transcribe_result.stdout
    assert "Transcripcion completada" in transcribe_result.stdout


def test_transcribe_command_requires_extraction_first(tmp_path: Path) -> None:
    from movie_translator.core.models import create_project

    projects_root = tmp_path / "projects"
    create_project(projects_root, "demo", source_language="en", target_language="es")

    result = runner.invoke(app, ["transcribe", "demo", "--projects-root", str(projects_root)])

    assert result.exit_code == 1
    assert "extraction" in result.stdout


def test_transcribe_command_missing_project(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["transcribe", "no_existe", "--projects-root", str(tmp_path / "projects")]
    )

    assert result.exit_code == 1
    assert "Error" in result.stdout


def test_translate_command_end_to_end(
    monkeypatch: pytest.MonkeyPatch, sample_video_with_audio: Path, tmp_path: Path
) -> None:
    from movie_translator.core.models import StageName, StageStatus, save_segments
    from movie_translator.core.pipeline.transcription import TRANSCRIPT_FILENAME

    projects_root = tmp_path / "projects"

    def fake_run_transcription(project, paths, **kw):
        project.mark_stage(StageName.TRANSCRIPTION, StageStatus.COMPLETED)
        project.save(paths.project_json)
        return project

    monkeypatch.setattr(cli_main, "run_transcription", fake_run_transcription)

    new_result = runner.invoke(
        app,
        ["new", str(sample_video_with_audio), "--name", "demo", "--projects-root", str(projects_root)],
    )
    assert new_result.exit_code == 0, new_result.stdout

    runner.invoke(app, ["transcribe", "demo", "--projects-root", str(projects_root)])
    # run_transcription esta mockeado (no escribe el json real): lo dejamos nosotros
    save_segments(_FAKE_SEGMENTS, projects_root / "demo" / "transcription" / TRANSCRIPT_FILENAME)

    def fake_get_provider(name, **kwargs):
        class _FakeProvider:
            def translate(self, lines, **kw):
                return [line.upper() for line in lines]

        return _FakeProvider()

    monkeypatch.setattr(cli_main, "get_provider", fake_get_provider)

    translate_result = runner.invoke(
        app, ["translate", "demo", "--projects-root", str(projects_root)]
    )

    assert translate_result.exit_code == 0, translate_result.stdout
    assert "Traduccion completada" in translate_result.stdout
    assert "✓ translation" in translate_result.stdout


def test_translate_command_requires_transcription_first(
    sample_video_with_audio: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    projects_root = tmp_path / "projects"
    new_result = runner.invoke(
        app,
        ["new", str(sample_video_with_audio), "--name", "demo", "--projects-root", str(projects_root)],
    )
    assert new_result.exit_code == 0, new_result.stdout

    result = runner.invoke(app, ["translate", "demo", "--projects-root", str(projects_root)])

    assert result.exit_code == 1
    assert "transcription" in result.stdout


def test_translate_command_unknown_provider_reports_error(tmp_path: Path) -> None:
    from movie_translator.core.models import StageName, StageStatus, create_project

    projects_root = tmp_path / "projects"
    project, paths = create_project(
        projects_root, "demo", source_language="en", target_language="es"
    )
    project.mark_stage(StageName.TRANSCRIPTION, StageStatus.COMPLETED)
    project.save(paths.project_json)

    result = runner.invoke(
        app,
        ["translate", "demo", "--provider", "deepseek", "--projects-root", str(projects_root)],
    )

    assert result.exit_code == 1
    assert "anthropic, openai, ollama" in result.stdout
