"""Generacion de subtitulos `.srt` a partir de segmentos traducidos.

Ver docs/ARCHITECTURE.md, seccion 8, para las reglas de legibilidad que
aplica `generate.build_cues`.
"""

from __future__ import annotations

from movie_translator.subtitles.generate import (
    build_cues,
    cue_warnings,
    cues_to_srt,
    generate_srt,
    write_srt,
)
from movie_translator.subtitles.rules import (
    MAX_CHARS_PER_LINE,
    MAX_CPS,
    MAX_LINES,
    MIN_DURATION_SECONDS,
    SubtitleCue,
    compute_cps,
    wrap_text,
)

__all__ = [
    "MAX_CHARS_PER_LINE",
    "MAX_CPS",
    "MAX_LINES",
    "MIN_DURATION_SECONDS",
    "SubtitleCue",
    "build_cues",
    "compute_cps",
    "cue_warnings",
    "cues_to_srt",
    "generate_srt",
    "wrap_text",
    "write_srt",
]
