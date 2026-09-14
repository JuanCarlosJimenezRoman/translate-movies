"""Tests de core/pipeline/translation.py (run_translation), con un
TranslationProvider falso -- no depende de ningun proveedor real."""

from __future__ import annotations

from pathlib import Path

import pytest

from movie_translator.core.models import (
    Project,
    Segment,
    StageName,
    StageStatus,
    create_project,
    load_segments,
    save_segments,
)
from movie_translator.core.pipeline import TRANSLATED_FILENAME, run_translation
from movie_translator.core.pipeline.transcription import TRANSCRIPT_FILENAME
from movie_translator.translation.glossary import GLOSSARY_FILENAME, load_glossary
from movie_translator.translation.providers.base import TranslationProvider
from movie_translator.translation.providers.errors import TranslationError

_ORIGINAL_SEGMENTS = [
    Segment(start=0.0, end=1.0, text="hello", confidence=0.9),
    Segment(start=1.0, end=2.0, text="world", confidence=0.8),
]


class _UppercaseProvider(TranslationProvider):
    """Traductor falso: devuelve cada linea en mayusculas. Registra sus llamadas."""

    def __init__(self) -> None:
        self.calls: list[dict] = []

    def translate(self, lines, *, source_language, target_language, glossary, speakers=None):
        self.calls.append(
            {
                "lines": list(lines),
                "source_language": source_language,
                "target_language": target_language,
                "glossary": dict(glossary),
                "speakers": speakers,
            }
        )
        return [line.upper() for line in lines]


class _RaisingProvider(TranslationProvider):
    def translate(self, lines, *, source_language, target_language, glossary, speakers=None):
        raise TranslationError("boom")


def _project_with_transcript(tmp_path: Path, name: str = "matrix"):
    project, paths = create_project(
        tmp_path / "projects", name, source_language="en", target_language="es"
    )
    save_segments(_ORIGINAL_SEGMENTS, paths.transcription / TRANSCRIPT_FILENAME)
    return project, paths


def test_run_translation_completes_and_saves_segments(tmp_path: Path) -> None:
    project, paths = _project_with_transcript(tmp_path)
    provider = _UppercaseProvider()

    run_translation(project, paths, provider)

    assert project.stages[StageName.TRANSLATION] == StageStatus.COMPLETED

    translated = load_segments(paths.translation / TRANSLATED_FILENAME)
    assert [s.text for s in translated] == ["HELLO", "WORLD"]
    # start/end/confidence del original se preservan, solo cambia el texto
    assert translated[0].start == 0.0
    assert translated[0].confidence == 0.9

    reloaded = Project.load(paths.project_json)
    assert reloaded.stages[StageName.TRANSLATION] == StageStatus.COMPLETED


def test_run_translation_passes_languages_and_glossary(tmp_path: Path) -> None:
    project, paths = _project_with_transcript(tmp_path)
    glossary_path = paths.translation / GLOSSARY_FILENAME
    glossary_path.parent.mkdir(parents=True, exist_ok=True)
    glossary_path.write_text('{"the Matrix": "la Matrix"}', encoding="utf-8")
    provider = _UppercaseProvider()

    run_translation(project, paths, provider)

    assert provider.calls[0]["source_language"] == "en"
    assert provider.calls[0]["target_language"] == "es"
    assert provider.calls[0]["glossary"] == {"the Matrix": "la Matrix"}


def test_run_translation_batches_by_batch_size(tmp_path: Path) -> None:
    project, paths = create_project(
        tmp_path / "projects", "matrix", source_language="en", target_language="es"
    )
    segments = [Segment(start=float(i), end=float(i + 1), text=f"line{i}") for i in range(5)]
    save_segments(segments, paths.transcription / TRANSCRIPT_FILENAME)
    provider = _UppercaseProvider()

    run_translation(project, paths, provider, batch_size=2)

    assert [len(call["lines"]) for call in provider.calls] == [2, 2, 1]
    translated = load_segments(paths.translation / TRANSLATED_FILENAME)
    assert [s.text for s in translated] == ["LINE0", "LINE1", "LINE2", "LINE3", "LINE4"]


def test_run_translation_saves_glossary_file(tmp_path: Path) -> None:
    project, paths = _project_with_transcript(tmp_path)

    run_translation(project, paths, _UppercaseProvider())

    glossary = load_glossary(paths.translation / GLOSSARY_FILENAME)
    assert glossary == {}


def test_run_translation_requires_transcription(tmp_path: Path) -> None:
    project, paths = create_project(
        tmp_path / "projects", "sintranscribir", source_language="en", target_language="es"
    )

    with pytest.raises(FileNotFoundError):
        run_translation(project, paths, _UppercaseProvider())

    assert project.stages[StageName.TRANSLATION] == StageStatus.PENDING


def test_run_translation_marks_failed_on_provider_error(tmp_path: Path) -> None:
    project, paths = _project_with_transcript(tmp_path)

    with pytest.raises(TranslationError):
        run_translation(project, paths, _RaisingProvider())

    assert project.stages[StageName.TRANSLATION] == StageStatus.FAILED

    reloaded = Project.load(paths.project_json)
    assert reloaded.stages[StageName.TRANSLATION] == StageStatus.FAILED


def test_run_translation_passes_speaker_names(tmp_path: Path) -> None:
    """Fase 2: si hay speakers.json, cada linea va acompanada del personaje
    que la dice (por indice dentro del lote); sin hablante asignado, la
    linea no aparece en el dict; con hablante detectado pero sin nombrar
    todavia, se usa la etiqueta cruda (SPEAKER_NN) como mejor esfuerzo."""
    from movie_translator.transcription.diarization import SpeakerInfo, save_speakers

    project, paths = create_project(
        tmp_path / "projects", "matrix", source_language="en", target_language="es"
    )
    segments = [
        Segment(start=0.0, end=1.0, text="hello", speaker="SPEAKER_00"),
        Segment(start=1.0, end=2.0, text="world", speaker="SPEAKER_01"),
        Segment(start=2.0, end=3.0, text="silence", speaker=None),
    ]
    save_segments(segments, paths.transcription / TRANSCRIPT_FILENAME)
    save_speakers(
        {
            "SPEAKER_00": SpeakerInfo(character="Neo"),
            "SPEAKER_01": SpeakerInfo(character=None),
        },
        paths.speakers_json,
    )
    provider = _UppercaseProvider()

    run_translation(project, paths, provider)

    assert provider.calls[0]["speakers"] == {"0": "Neo", "1": "SPEAKER_01"}


def test_run_translation_speakers_none_without_diarization(tmp_path: Path) -> None:
    """Sin speakers.json (proyecto sin diarizar, como en Fase 1), el
    comportamiento es identico: se pasa `speakers=None`."""
    project, paths = _project_with_transcript(tmp_path)
    provider = _UppercaseProvider()

    run_translation(project, paths, provider)

    assert provider.calls[0]["speakers"] is None
