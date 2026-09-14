"""Etapa de traduccion: segmentos transcritos -> segmentos traducidos."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from typing import TypeVar

from movie_translator.core.models import Project, ProjectPaths, StageName, StageStatus
from movie_translator.core.models.segment import Segment, load_segments, save_segments
from movie_translator.core.pipeline.transcription import TRANSCRIPT_FILENAME
from movie_translator.transcription.diarization import SpeakerInfo, load_speakers
from movie_translator.translation.glossary import GLOSSARY_FILENAME, load_glossary, save_glossary
from movie_translator.translation.providers import TranslationProvider

TRANSLATED_FILENAME = "final.json"
DEFAULT_BATCH_SIZE = 40

T = TypeVar("T")


def _batched(items: Sequence[T], size: int) -> Iterator[Sequence[T]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _speaker_names_for_batch(
    batch: Sequence[Segment], speakers: dict[str, SpeakerInfo]
) -> dict[str, str] | None:
    """Arma el `speakers` que se le pasa a `TranslationProvider.translate()`.

    Claves: indice de la linea dentro del lote (como string, ver
    docs/ARCHITECTURE.md seccion 7 / TranslationProvider.translate). Una
    linea sin hablante asignado (todavia sin diarizar, o sin solapamiento
    con ningun turno) simplemente no aparece. Si un hablante fue detectado
    pero todavia no tiene nombre (checkpoint humano pendiente), se usa la
    etiqueta cruda (SPEAKER_NN) como mejor esfuerzo, para no perder del todo
    la senal de "es siempre el mismo personaje".
    """
    names: dict[str, str] = {}
    for i, segment in enumerate(batch):
        if segment.speaker is None:
            continue
        info = speakers.get(segment.speaker)
        names[str(i)] = info.character if info and info.character else segment.speaker
    return names or None


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
    proyecto como contexto en cada lote. Si el proyecto ya paso por
    diarizacion (`transcription/speakers.json` existe), tambien pasa el
    personaje de cada linea (Fase 2); si no, se comporta igual que en la
    Fase 1. Igual que las etapas anteriores, cualquier fallo marca la etapa
    como FAILED y persiste el estado antes de relanzar la excepcion.
    """
    transcript_path = paths.transcription / TRANSCRIPT_FILENAME
    if not transcript_path.exists():
        raise FileNotFoundError(
            f"No existe {transcript_path}. Corre 'movie-translator transcribe' primero."
        )

    segments = load_segments(transcript_path)
    glossary_path = paths.translation / GLOSSARY_FILENAME
    glossary = load_glossary(glossary_path)
    speakers = load_speakers(paths.speakers_json)

    project.mark_stage(StageName.TRANSLATION, StageStatus.RUNNING)
    project.save(paths.project_json)

    try:
        translated_segments: list[Segment] = []
        for batch in _batched(segments, batch_size):
            texts = [segment.text for segment in batch]
            speaker_names = _speaker_names_for_batch(batch, speakers)
            translated_texts = provider.translate(
                texts,
                source_language=project.source_language,
                target_language=project.target_language,
                glossary=glossary,
                speakers=speaker_names,
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
