"""Tests de subtitles/rules.py: wrap_text y compute_cps."""

from __future__ import annotations

from movie_translator.subtitles.rules import compute_cps, wrap_text


def test_wrap_text_short_line_fits_one_line() -> None:
    lines, exceeds = wrap_text("hola mundo", max_chars_per_line=42, max_lines=2)

    assert lines == ["hola mundo"]
    assert exceeds is False


def test_wrap_text_wraps_long_text_into_multiple_lines() -> None:
    text = "esto es una linea bastante larga que no entra en cuarenta y dos caracteres"

    lines, exceeds = wrap_text(text, max_chars_per_line=42, max_lines=2)

    assert len(lines) == 2
    assert all(len(line) <= 42 for line in lines)
    assert exceeds is False


def test_wrap_text_flags_when_more_lines_than_allowed() -> None:
    text = " ".join(["palabra"] * 30)  # bien mas largo que 2 lineas de 42 caracteres

    lines, exceeds = wrap_text(text, max_chars_per_line=42, max_lines=2)

    assert len(lines) > 2
    assert exceeds is True
    # el contenido no se pierde: todas las palabras siguen presentes
    assert sum(line.count("palabra") for line in lines) == 30


def test_wrap_text_normalizes_whitespace() -> None:
    lines, _ = wrap_text("  hola   mundo  \n\tcomo estas  ")

    assert lines == ["hola mundo como estas"]


def test_wrap_text_empty_text_returns_no_lines() -> None:
    lines, exceeds = wrap_text("   ")

    assert lines == []
    assert exceeds is False


def test_compute_cps_basic() -> None:
    # "hola" son 4 caracteres en 2 segundos -> 2 CPS
    assert compute_cps("hola", 2.0) == 2.0


def test_compute_cps_ignores_newlines() -> None:
    assert compute_cps("ab\ncd", 2.0) == 2.0  # 4 caracteres reales, no 5


def test_compute_cps_zero_duration_is_infinite() -> None:
    assert compute_cps("hola", 0.0) == float("inf")
