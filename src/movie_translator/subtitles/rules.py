"""Reglas de legibilidad de subtitulos (docs/ARCHITECTURE.md, seccion 8).

Estos valores son estandares de industria (rondan lo que usan Netflix/BBC
para subtitulado): por encima de ~17 caracteres por segundo el espectador no
llega a leer el cue completo, mas de 2 lineas o 42 caracteres por linea no
entran comodamente en pantalla, y un cue de menos de 1s es un "subtitulo de
flash" que aparece y desaparece antes de que el ojo se fije en el.
"""

from __future__ import annotations

import textwrap
from dataclasses import dataclass, field

MAX_CPS = 17.0
MAX_LINES = 2
MAX_CHARS_PER_LINE = 42
MIN_DURATION_SECONDS = 1.0


@dataclass
class SubtitleCue:
    """Un cue listo para escribirse a `.srt`: texto ya envuelto + tiempos.

    `warnings` queda no vacio cuando el cue no cumple alguna regla (ver
    `subtitles.generate.build_cues`) y no se pudo corregir automaticamente --
    se genera igual, pero marcado para revision, tal como pide
    ARCHITECTURE.md seccion 8 ("marca los cues que no cumplen para revision
    o para pedirle al traductor una version mas corta").
    """

    index: int
    start: float
    end: float
    lines: list[str]
    warnings: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(self.lines)

    @property
    def duration(self) -> float:
        return self.end - self.start


def wrap_text(
    text: str,
    *,
    max_chars_per_line: int = MAX_CHARS_PER_LINE,
    max_lines: int = MAX_LINES,
) -> tuple[list[str], bool]:
    """Envuelve `text` en lineas de a lo sumo `max_chars_per_line` caracteres.

    No trunca el contenido aunque el resultado supere `max_lines`: perder
    parte de una traduccion para que "quepa" es peor que un cue con una
    linea de mas, y esto ultimo es justamente lo que la regla de "marcar
    para revision" esta pensada para señalar. Devuelve `(lineas, excede)`,
    donde `excede` es True si el numero de lineas resultante es mayor a
    `max_lines`.
    """
    normalized = " ".join(text.split())
    if not normalized:
        return [], False

    lines = textwrap.wrap(normalized, width=max_chars_per_line) or [""]
    exceeds_max_lines = len(lines) > max_lines
    return lines, exceeds_max_lines


def compute_cps(text: str, duration: float) -> float:
    """Caracteres por segundo de un cue (saltos de linea no cuentan)."""
    if duration <= 0:
        return float("inf")
    char_count = len(text.replace("\n", ""))
    return char_count / duration
