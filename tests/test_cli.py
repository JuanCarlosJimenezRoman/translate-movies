"""Tests de extremo a extremo del CLI (apps/cli/main.py) via CliRunner."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from apps.cli.main import app

runner = CliRunner()


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
