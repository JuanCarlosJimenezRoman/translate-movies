"""Tests de subtitles/generate.py: build_cues, cues_to_srt, write_srt."""

from __future__ import annotations

from pathlib import Path

import srt as srt_lib

from movie_translator.core.models.segment import Segment
from movie_translator.subtitles.generate import build_cues, cues_to_srt, generate_srt, write_srt


def test_build_cues_basic_ordering_and_numbering() -> None:
    segments = [
        Segment(start=5.0, end=7.0, text="segunda"),
        Segment(start=0.0, end=2.0, text="primera"),
    ]

    cues = build_cues(segments)

    assert [cue.text for cue in cues] == ["primera", "segunda"]
    assert [cue.index for cue in cues] == [1, 2]


def test_build_cues_extends_short_cue_to_min_duration() -> None:
    segments = [Segment(start=0.0, end=0.3, text="hola")]

    cues = build_cues(segments, min_duration=1.0)

    assert cues[0].duration >= 1.0
    assert cues[0].warnings == []


def test_build_cues_does_not_extend_past_next_segment_start() -> None:
    segments = [
        Segment(start=0.0, end=0.3, text="hola"),
        Segment(start=0.5, end=1.5, text="mundo"),
    ]

    cues = build_cues(segments, min_duration=1.0)

    assert cues[0].end <= 0.5
    assert any("flash" in w for w in cues[0].warnings)


def test_build_cues_flags_high_cps_without_altering_text() -> None:
    long_text = "una traduccion demasiado larga para el tiempo tan corto disponible aqui"
    segments = [Segment(start=0.0, end=1.0, text=long_text)]

    cues = build_cues(segments)

    assert cues[0].text.replace("\n", " ") == long_text
    assert any("CPS" in w for w in cues[0].warnings)


def test_build_cues_flags_line_overflow_without_truncating() -> None:
    long_text = " ".join(["palabra"] * 30)
    segments = [Segment(start=0.0, end=100.0, text=long_text)]

    cues = build_cues(segments)

    assert cues[0].text.count("palabra") == 30
    assert any("lineas" in w for w in cues[0].warnings)


def test_build_cues_drops_empty_segments() -> None:
    segments = [
        Segment(start=0.0, end=1.0, text="   "),
        Segment(start=1.0, end=2.0, text="hola"),
    ]

    cues = build_cues(segments)

    assert len(cues) == 1
    assert cues[0].text == "hola"
    assert cues[0].index == 1


def test_cues_to_srt_produces_parseable_output() -> None:
    segments = [Segment(start=0.0, end=2.0, text="hola mundo")]

    cues = build_cues(segments)
    srt_text = cues_to_srt(cues)
    parsed = list(srt_lib.parse(srt_text))

    assert len(parsed) == 1
    assert parsed[0].content == "hola mundo"
    assert parsed[0].start.total_seconds() == 0.0
    assert parsed[0].end.total_seconds() == 2.0


def test_write_srt_creates_file_and_parent_dirs(tmp_path: Path) -> None:
    segments = [Segment(start=0.0, end=2.0, text="hola")]
    output_path = tmp_path / "subtitles" / "es.srt"

    cues = build_cues(segments)
    write_srt(cues, output_path)

    assert output_path.exists()
    parsed = list(srt_lib.parse(output_path.read_text(encoding="utf-8")))
    assert parsed[0].content == "hola"


def test_generate_srt_returns_warnings_and_writes_file(tmp_path: Path) -> None:
    segments = [
        Segment(start=0.0, end=2.0, text="hola mundo"),
        Segment(start=2.0, end=2.1, text="rapido"),  # ultimo segmento: se puede extender libre
    ]
    output_path = tmp_path / "es.srt"

    warnings = generate_srt(segments, output_path, min_duration=1.0)

    assert output_path.exists()
    assert warnings == []  # ambos cues terminan cumpliendo todas las reglas
