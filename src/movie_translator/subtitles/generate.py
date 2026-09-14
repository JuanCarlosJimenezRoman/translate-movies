"""Genera un `.srt` a partir de segmentos traducidos.

Aplica las reglas de legibilidad de docs/ARCHITECTURE.md seccion 8 (CPS,
lineas/caracteres por cue, duracion minima) y marca con warnings los cues
que no las cumplen, en vez de alterar en silencio el texto traducido.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import srt as srt_lib

from movie_translator.core.models.segment import Segment
from movie_translator.subtitles.rules import (
    MAX_CHARS_PER_LINE,
    MAX_CPS,
    MAX_LINES,
    MIN_DURATION_SECONDS,
    SubtitleCue,
    compute_cps,
    wrap_text,
)


def build_cues(
    segments: list[Segment],
    *,
    max_cps: float = MAX_CPS,
    max_lines: int = MAX_LINES,
    max_chars_per_line: int = MAX_CHARS_PER_LINE,
    min_duration: float = MIN_DURATION_SECONDS,
) -> list[SubtitleCue]:
    """Convierte segmentos (con texto ya traducido) en cues listos para `.srt`.

    Por cada segmento, en orden de tiempo:

    1. envuelve el texto a `max_lines` x `max_chars_per_line` (sin truncar,
       ver `rules.wrap_text`);
    2. si el cue dura menos que `min_duration` (subtitulo de flash), extiende
       su fin hasta `min_duration`, pero nunca mas alla del inicio del
       siguiente segmento -- no se generan cues superpuestos;
    3. calcula el CPS resultante; si supera `max_cps`, **no se acorta el
       texto** (eso cambiaria la traduccion) -- se deja como warning, porque
       lo que corresponde es pedir una traduccion mas corta (seccion 7), no
       mutilar el texto automaticamente.

    Los segmentos con texto vacio (tras normalizar espacios) se descartan:
    no hay nada que mostrar. El resto se numera consecutivamente.
    """
    ordered = sorted(segments, key=lambda s: s.start)
    cues: list[SubtitleCue] = []

    for i, segment in enumerate(ordered):
        lines, exceeds_lines = wrap_text(
            segment.text, max_chars_per_line=max_chars_per_line, max_lines=max_lines
        )
        if not lines:
            continue

        warnings: list[str] = []
        if exceeds_lines:
            warnings.append(
                f"{len(lines)} lineas (recomendado maximo {max_lines}): "
                "revisar traduccion o acortarla"
            )

        start, end = segment.start, segment.end
        duration = end - start
        if duration < min_duration:
            next_start = ordered[i + 1].start if i + 1 < len(ordered) else None
            extended_end = start + min_duration
            if next_start is not None:
                extended_end = min(extended_end, next_start)
            end = max(end, extended_end)
            if end - start < min_duration:
                warnings.append(
                    f"cue de flash: dura {duration:.2f}s (minimo {min_duration}s) "
                    "y no se pudo extender sin superponerse al siguiente cue"
                )

        cps = compute_cps("\n".join(lines), end - start)
        if cps > max_cps:
            warnings.append(
                f"CPS {cps:.1f} por encima del maximo {max_cps}: traduccion "
                "demasiado larga para el tiempo disponible"
            )

        cues.append(SubtitleCue(index=0, start=start, end=end, lines=lines, warnings=warnings))

    for position, cue in enumerate(cues, start=1):
        cue.index = position

    return cues


def cues_to_srt(cues: list[SubtitleCue]) -> str:
    """Serializa cues a texto `.srt` (formato SubRip estandar)."""
    subtitles = [
        srt_lib.Subtitle(
            index=cue.index,
            start=timedelta(seconds=cue.start),
            end=timedelta(seconds=cue.end),
            content=cue.text,
        )
        for cue in cues
    ]
    return srt_lib.compose(subtitles)


def write_srt(cues: list[SubtitleCue], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(cues_to_srt(cues), encoding="utf-8")


def cue_warnings(cues: list[SubtitleCue]) -> list[str]:
    """Aplana los warnings de todos los cues en lineas listas para mostrar."""
    return [
        f"cue {cue.index} [{cue.start:.2f}s-{cue.end:.2f}s]: {warning}"
        for cue in cues
        for warning in cue.warnings
    ]


def generate_srt(
    segments: list[Segment],
    output_path: Path,
    *,
    max_cps: float = MAX_CPS,
    max_lines: int = MAX_LINES,
    max_chars_per_line: int = MAX_CHARS_PER_LINE,
    min_duration: float = MIN_DURATION_SECONDS,
) -> list[str]:
    """Genera el `.srt` en `output_path` y devuelve los warnings encontrados."""
    cues = build_cues(
        segments,
        max_cps=max_cps,
        max_lines=max_lines,
        max_chars_per_line=max_chars_per_line,
        min_duration=min_duration,
    )
    write_srt(cues, output_path)
    return cue_warnings(cues)
