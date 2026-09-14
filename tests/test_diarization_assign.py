"""Tests de transcription/diarization/turns.py (asignacion de hablante por
mayor solapamiento de tiempo, ver docs/DECISIONES.md)."""

from __future__ import annotations

from movie_translator.core.models.segment import Segment
from movie_translator.transcription.diarization.turns import SpeakerTurn, assign_speakers


def test_assign_speakers_picks_matching_turn() -> None:
    segments = [Segment(start=0.0, end=2.0, text="hola")]
    turns = [SpeakerTurn(start=0.0, end=2.0, speaker="SPEAKER_00")]

    result = assign_speakers(segments, turns)

    assert result[0].speaker == "SPEAKER_00"


def test_assign_speakers_picks_turn_with_most_overlap() -> None:
    # El segmento se solapa con ambos turnos, pero mas tiempo con SPEAKER_01.
    segments = [Segment(start=0.0, end=10.0, text="hola")]
    turns = [
        SpeakerTurn(start=0.0, end=3.0, speaker="SPEAKER_00"),
        SpeakerTurn(start=3.0, end=10.0, speaker="SPEAKER_01"),
    ]

    result = assign_speakers(segments, turns)

    assert result[0].speaker == "SPEAKER_01"


def test_assign_speakers_no_overlap_leaves_speaker_none() -> None:
    segments = [Segment(start=0.0, end=1.0, text="hola")]
    turns = [SpeakerTurn(start=5.0, end=6.0, speaker="SPEAKER_00")]

    result = assign_speakers(segments, turns)

    assert result[0].speaker is None


def test_assign_speakers_no_turns_at_all_leaves_speaker_none() -> None:
    segments = [Segment(start=0.0, end=1.0, text="hola")]

    result = assign_speakers(segments, [])

    assert result[0].speaker is None


def test_assign_speakers_preserves_order_and_other_fields() -> None:
    segments = [
        Segment(start=0.0, end=1.0, text="uno", confidence=0.5),
        Segment(start=1.0, end=2.0, text="dos", confidence=0.9),
    ]
    turns = [
        SpeakerTurn(start=0.0, end=1.0, speaker="SPEAKER_00"),
        SpeakerTurn(start=1.0, end=2.0, speaker="SPEAKER_01"),
    ]

    result = assign_speakers(segments, turns)

    assert [s.text for s in result] == ["uno", "dos"]
    assert [s.speaker for s in result] == ["SPEAKER_00", "SPEAKER_01"]
    assert [s.confidence for s in result] == [0.5, 0.9]


def test_assign_speakers_does_not_mutate_input() -> None:
    segments = [Segment(start=0.0, end=1.0, text="hola")]
    turns = [SpeakerTurn(start=0.0, end=1.0, speaker="SPEAKER_00")]

    assign_speakers(segments, turns)

    assert segments[0].speaker is None
