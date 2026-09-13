"""Etapa de transcripcion: audio extraido -> segmentos con timestamps."""

from __future__ import annotations

from pathlib import Path

from movie_translator.core.models import Project, ProjectPaths, StageName, StageStatus
from movie_translator.core.models.segment import save_segments
from movie_translator.core.pipeline.extraction import ORIGINAL_AUDIO_FILENAME
from movie_translator.transcription.whisper import (
    DEFAULT_MODEL_SIZE,
    DEFAULT_MODELS_DIR,
    transcribe_audio,
)

TRANSCRIPT_FILENAME = "original.json"


def run_transcription(
    project: Project,
    paths: ProjectPaths,
    *,
    model_size: str = DEFAULT_MODEL_SIZE,
    models_dir: Path = DEFAULT_MODELS_DIR,
) -> Project:
    """Transcribe el audio ya extraido y guarda los segmentos en `transcription/`.

    Requiere que la etapa de extraccion ya haya terminado (necesita
    `paths.audio/original.wav`). Igual que `run_extraction`, cualquier fallo
    marca la etapa como FAILED y persiste el estado antes de relanzar la
    excepcion, para que el proyecto nunca quede a medias sin que se note.
    """
    audio_path = paths.audio / ORIGINAL_AUDIO_FILENAME
    if not audio_path.exists():
        raise FileNotFoundError(
            f"No existe {audio_path}. Corre 'movie-translator new' primero "
            "para extraer el audio del video."
        )

    project.mark_stage(StageName.TRANSCRIPTION, StageStatus.RUNNING)
    project.save(paths.project_json)

    try:
        segments = transcribe_audio(
            audio_path,
            model_size=model_size,
            language=project.source_language,
            models_dir=models_dir,
        )
        save_segments(segments, paths.transcription / TRANSCRIPT_FILENAME)
    except Exception:
        project.mark_stage(StageName.TRANSCRIPTION, StageStatus.FAILED)
        project.save(paths.project_json)
        raise

    project.mark_stage(StageName.TRANSCRIPTION, StageStatus.COMPLETED)
    project.save(paths.project_json)
    return project
