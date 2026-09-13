"""Modelo de datos de un proyecto (una pelicula) y su persistencia.

Ver docs/ARCHITECTURE.md, secciones 5 y 6: cada pelicula vive en
`projects/<nombre>/` con subcarpetas por tipo de artefacto y un
`project.json` que registra el estado de cada etapa. Esto es lo que permite
reanudar el pipeline sin reprocesar lo que ya se hizo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from movie_translator.core.models.stage import (
    STAGE_ORDER,
    STAGE_STATUS_SYMBOL,
    StageName,
    StageStatus,
)

_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _default_stages() -> dict[StageName, StageStatus]:
    return {stage: StageStatus.PENDING for stage in STAGE_ORDER}


class Project(BaseModel):
    """Estado de una pelicula dentro de `projects/<name>/project.json`."""

    name: str
    source_language: str
    target_language: str
    source_file: str | None = Field(
        default=None,
        description="Ruta relativa a la raiz del proyecto, ej. 'source/matrix.mkv'",
    )
    duration_seconds: float | None = None
    stages: dict[StageName, StageStatus] = Field(default_factory=_default_stages)
    created_at: datetime = Field(default_factory=_utc_now)
    updated_at: datetime = Field(default_factory=_utc_now)

    # -- estado de etapas -------------------------------------------------

    def mark_stage(self, stage: StageName, status: StageStatus) -> None:
        """Actualiza el estado de una etapa y el timestamp de modificacion."""
        self.stages[stage] = status
        self.updated_at = _utc_now()

    def is_completed(self, stage: StageName) -> bool:
        return self.stages.get(stage) == StageStatus.COMPLETED

    def pending_stage(self) -> StageName | None:
        """Primera etapa (en orden de pipeline) que todavia no esta completada.

        Devuelve None si todo el pipeline ya termino. Es lo que usa el CLI
        para saber por donde reanudar.
        """
        for stage in STAGE_ORDER:
            if self.stages.get(stage) != StageStatus.COMPLETED:
                return stage
        return None

    def progress_lines(self) -> list[str]:
        """Lineas tipo '✓ extraction' / '→ translation' / '○ tts', en orden."""
        return [
            f"{STAGE_STATUS_SYMBOL[self.stages.get(stage, StageStatus.PENDING)]} {stage.value}"
            for stage in STAGE_ORDER
        ]

    # -- persistencia -------------------------------------------------------

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.model_dump_json(indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> Project:
        if not path.exists():
            raise FileNotFoundError(f"No existe project.json: {path}")
        return cls.model_validate_json(path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class ProjectPaths:
    """Layout de carpetas de `projects/<name>/` (docs/ARCHITECTURE.md, seccion 5)."""

    root: Path

    @property
    def source(self) -> Path:
        return self.root / "source"

    @property
    def audio(self) -> Path:
        return self.root / "audio"

    @property
    def transcription(self) -> Path:
        return self.root / "transcription"

    @property
    def translation(self) -> Path:
        return self.root / "translation"

    @property
    def voices(self) -> Path:
        return self.root / "voices"

    @property
    def subtitles(self) -> Path:
        return self.root / "subtitles"

    @property
    def output(self) -> Path:
        return self.root / "output"

    @property
    def project_json(self) -> Path:
        return self.root / "project.json"

    def ensure_dirs(self) -> None:
        for path in (
            self.source,
            self.audio,
            self.transcription,
            self.translation,
            self.voices,
            self.subtitles,
            self.output,
        ):
            path.mkdir(parents=True, exist_ok=True)


def _validate_name(name: str) -> None:
    if not _NAME_RE.match(name):
        raise ValueError(
            f"Nombre de proyecto invalido: {name!r}. Usa minusculas, numeros, "
            "'-' o '_', empezando por una letra o numero (ej. 'matrix', "
            "'blade-runner-2049')."
        )


def create_project(
    projects_root: Path,
    name: str,
    *,
    source_language: str,
    target_language: str,
) -> tuple[Project, ProjectPaths]:
    """Crea la carpeta `projects/<name>/` y su `project.json` inicial.

    Lanza ValueError si el nombre no es valido, y FileExistsError si el
    proyecto ya existe (para no pisar un pipeline que ya esta en curso).
    """
    _validate_name(name)
    paths = ProjectPaths(root=projects_root / name)
    if paths.root.exists():
        raise FileExistsError(
            f"El proyecto '{name}' ya existe en {paths.root}. Usa "
            "load_project() para continuarlo."
        )

    paths.ensure_dirs()
    project = Project(
        name=name,
        source_language=source_language,
        target_language=target_language,
    )
    project.save(paths.project_json)
    return project, paths


def load_project(projects_root: Path, name: str) -> tuple[Project, ProjectPaths]:
    """Carga un proyecto existente por nombre."""
    paths = ProjectPaths(root=projects_root / name)
    project = Project.load(paths.project_json)
    return project, paths
