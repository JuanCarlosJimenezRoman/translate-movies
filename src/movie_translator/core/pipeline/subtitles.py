"""Etapa de subtitulos: segmentos traducidos -> `.srt` final."""

from __future__ import annotations

from movie_translator.core.models import Project, ProjectPaths, StageName, StageStatus
from movie_translator.core.models.segment import load_segments
from movie_translator.core.pipeline.translation import TRANSLATED_FILENAME
from movie_translator.subtitles import generate_srt


def subtitles_filename(project: Project) -> str:
    return f"{project.target_language}.srt"


def run_subtitles(project: Project, paths: ProjectPaths) -> tuple[Project, list[str]]:
    """Genera el `.srt` final a partir de `translation/final.json`.

    Requiere que la traduccion ya haya terminado. Devuelve el proyecto
    actualizado y la lista de warnings de cues que no cumplen las reglas de
    legibilidad (docs/ARCHITECTURE.md seccion 8) -- el `.srt` se genera
    igual, marcados para revision, no se bloquea la etapa por esto.
    """
    translated_path = paths.translation / TRANSLATED_FILENAME
    if not translated_path.exists():
        raise FileNotFoundError(
            f"No existe {translated_path}. Corre 'movie-translator translate' primero."
        )

    segments = load_segments(translated_path)

    project.mark_stage(StageName.SUBTITLES, StageStatus.RUNNING)
    project.save(paths.project_json)

    try:
        output_path = paths.subtitles / subtitles_filename(project)
        warnings = generate_srt(segments, output_path)
    except Exception:
        project.mark_stage(StageName.SUBTITLES, StageStatus.FAILED)
        project.save(paths.project_json)
        raise

    project.mark_stage(StageName.SUBTITLES, StageStatus.COMPLETED)
    project.save(paths.project_json)
    return project, warnings
