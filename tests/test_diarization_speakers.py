"""Tests de transcription/diarization/speakers.py (speakers.json)."""

from __future__ import annotations

from pathlib import Path

from movie_translator.transcription.diarization.speakers import (
    SpeakerInfo,
    load_speakers,
    save_speakers,
)


def test_load_speakers_missing_file_returns_empty(tmp_path: Path) -> None:
    assert load_speakers(tmp_path / "speakers.json") == {}


def test_save_and_load_speakers_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "transcription" / "speakers.json"
    speakers = {
        "SPEAKER_00": SpeakerInfo(character="Neo", voice=None),
        "SPEAKER_01": SpeakerInfo(),
    }

    save_speakers(speakers, path)
    loaded = load_speakers(path)

    assert loaded == speakers


def test_save_speakers_creates_parent_dirs(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "dir" / "speakers.json"

    save_speakers({"SPEAKER_00": SpeakerInfo(character="Neo")}, path)

    assert path.exists()


def test_speaker_info_defaults_to_unnamed() -> None:
    info = SpeakerInfo()

    assert info.character is None
    assert info.voice is None
