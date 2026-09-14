"""Etapa de traduccion: segmentos transcritos -> segmentos traducidos."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import TypeVar

from movie_translator.core.models import Project, ProjectPaths, StageName, StageStatus
from movie_translator.core.models.segment import Segment, load_segments, save_segments
from movie_translator.core.pipeline.transcription import TRANSCRIPT_FILENAME
from movie_translator.translation.glossary import GLOSSARY_FILENAME, load_glossary, save_glossary
from movie_translator.translation.providers import TranslationProvider

TRANSLATED_FILENAME = "final.json"
DEFAULT_BATCH_SIZE = 40

T = TypeVar("T")


def _batched(items: Sequence[T], size: int) -> Iterator[Sequence[T]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def run_translation(
    project: Project,
    paths: ProjectPaths,
    provider: TranslationProvider,
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> Project:
    """Traduce los segmentos ya transcritos y guarda el resultado + el glosario.

    Requiere que la transcripcion ya haya terminado. Traduce en lotes de
    `batch_size` lineas consecutivas -- no linea por linea de forma aislada
    (docs/ARCHITECTURE.md, seccion 7) -- pasando el glosario acumulado del
    proyecto como contexto en cada lote. Igual que las etapas anteriores,
    cualquier fallo marca la etapa como FAILED y persiste el estado antes de
    relanzar la excepcion.
    """
    transcript_path = paths.transcription / TRANSCRIPT_FILENAME
    if not transcript_path.exists():
        raise FileNotFoundError(
            f"No existe {transcript_path}. Corre 'movie-translator transcribe' primero."
        )

    segments = load_segments(transcript_path)
    glossary_path = paths.translation / GLOSSARY_FILENAME
    glossary = load_glossary(glossary_path)

    project.mark_stage(StageName.TRANSLATION, StageStatus.RUNNING)
    project.save(paths.project_json)

    try:
        translated_segments: list[Segment] = []
        for batch in _batched(segments, batch_size):
            texts = [segment.text for segment in batch]
            translated_texts = provider.translate(
                texts,
                source_language=project.source_language,
                target_language=project.target_language,
                glossary=glossary,
            )
            for original, translated_text in zip(batch, translated_texts, strict=True):
                translated_segments.append(original.model_copy(update={"text": translated_text}))

        save_segments(translated_segments, paths.translation / TRANSLATED_FILENAME)
        save_glossary(glossary, glossary_path)
    except Exception:
        project.mark_stage(StageName.TRANSLATION, StageStatus.FAILED)
        project.save(paths.project_json)
        raise

    project.mark_stage(StageName.TRANSLATION, StageStatus.COMPLETED)
    project.save(paths.project_json)
    return project
