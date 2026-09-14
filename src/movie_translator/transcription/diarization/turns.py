"""Turnos de hablante (salida de pyannote) y su asignacion a segmentos de Whisper.

Whisper y pyannote son dos salidas independientes con sus propios cortes de
tiempo: Whisper da segmentos de texto, pyannote da turnos de habla. No
calzan exacto, asi que hace falta una regla explicita para decidir que
hablante le corresponde a cada segmento (ver docs/DECISIONES.md).
"""

from __future__ import annotations

from dataclasses import dataclass

from movie_translator.core.models.segment import Segment


@dataclass(frozen=True)
class SpeakerTurn:
    """Un turno de habla detectado por pyannote: 'entre start y end habla X'."""

    start: float
    end: float
    speaker: str


def _overlap_seconds(seg: Segment, turn: SpeakerTurn) -> float:
    return max(0.0, min(seg.end, turn.end) - max(seg.start, turn.start))


def assign_speakers(segments: list[Segment], turns: list[SpeakerTurn]) -> list[Segment]:
    """Asigna a cada segmento el hablante del turno con mayor solapamiento de tiempo.

    Regla estandar (ver docs/DECISIONES.md): si un segmento se solapa con
    varios turnos, gana el que mas tiempo comparte con el. Si no se solapa
    con ninguno (voz superpuesta, ruido, turno no detectado), `speaker`
    queda en None para revision manual -- no se inventa un hablante.

    Devuelve una lista nueva (no muta `segments`), en el mismo orden.
    """
    result: list[Segment] = []
    for seg in segments:
        best_turn: SpeakerTurn | None = None
        best_overlap = 0.0
        for turn in turns:
            overlap = _overlap_seconds(seg, turn)
            if overlap > best_overlap:
                best_overlap = overlap
                best_turn = turn
        speaker = best_turn.speaker if best_turn is not None else None
        result.append(seg.model_copy(update={"speaker": speaker}))
    return result
