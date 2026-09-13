"""Modelos de datos del proyecto (ver docs/ARCHITECTURE.md, secciones 5 y 6)."""

from movie_translator.core.models.project import (
    Project,
    ProjectPaths,
    create_project,
    load_project,
)
from movie_translator.core.models.segment import Segment, load_segments, save_segments
from movie_translator.core.models.stage import (
    STAGE_ORDER,
    STAGE_STATUS_SYMBOL,
    StageName,
    StageStatus,
)

__all__ = [
    "STAGE_ORDER",
    "STAGE_STATUS_SYMBOL",
    "Project",
    "ProjectPaths",
    "Segment",
    "StageName",
    "StageStatus",
    "create_project",
    "load_project",
    "load_segments",
    "save_segments",
]
