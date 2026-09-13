"""Etapa de extraccion: video -> audio original dentro del proyecto.

Ver docs/ARCHITECTURE.md, secciones 3 y 13, y docs/DECISIONES.md. El video
fuente NO se copia dentro de `projects/<nombre>/source/`: se referencia por
su ruta absoluta en `project.source_file`, para no duplicar espacio de disco
en archivos que pueden pesar decenas de GB (`source/` queda disponible para
cuando se agregue un flag `--copy-source` opcional, si hace falta
portabilidad).
"""

from __future__ import annotations

from pathlib import Path

from movie_translator.core.models import Project, ProjectPaths, StageName, StageStatus
from movie_translator.media.ffmpeg import extract_audio, probe

ORIGINAL_AUDIO_FILENAME = "original.wav"


def run_extraction(project: Project, paths: ProjectPaths, source_video: Path) -> Project:
    """Extrae el audio de `source_video` a `paths.audio/original.wav`.

    Dejar el estado a medio camino (una etapa en "running" para siempre) es
    peor que fallar ruidosamente, asi que esta funcion marca la etapa como
    FAILED y persiste `project.json` ante *cualquier* error antes de volver a
    lanzarlo, sea cual sea su tipo. Quien llama decide como reportarlo.
    """
    source_video = source_video.resolve()
    if not source_video.exists():
        raise FileNotFoundError(f"No existe el archivo de video: {source_video}")

    project.mark_stage(StageName.EXTRACTION, StageStatus.RUNNING)
    project.save(paths.project_json)

    try:
        info = probe(source_video)
        extract_audio(source_video, paths.audio / ORIGINAL_AUDIO_FILENAME, overwrite=True)
    except Exception:
        project.mark_stage(StageName.EXTRACTION, StageStatus.FAILED)
        project.save(paths.project_json)
        raise

    project.source_file = str(source_video)
    project.duration_seconds = info.duration_seconds
    project.mark_stage(StageName.EXTRACTION, StageStatus.COMPLETED)
    project.save(paths.project_json)
    return project
