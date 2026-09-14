"""Tests de translation/providers/prompt.py (construccion de prompt y parseo)."""

from __future__ import annotations

import json

import pytest

from movie_translator.translation.providers.errors import TranslationError
from movie_translator.translation.providers.prompt import (
    build_system_prompt,
    build_user_message,
    parse_translation_response,
)


def test_build_system_prompt_includes_languages_and_count() -> None:
    prompt = build_system_prompt(
        source_language="en", target_language="es", line_count=3, glossary={}
    )

    assert "en" in prompt
    assert "es" in prompt
    assert "3" in prompt
    assert "vacio por ahora" in prompt


def test_build_system_prompt_includes_glossary_entries() -> None:
    prompt = build_system_prompt(
        source_language="en",
        target_language="es",
        line_count=1,
        glossary={"the Matrix": "la Matrix"},
    )

    assert "the Matrix" in prompt
    assert "la Matrix" in prompt


def test_build_user_message_is_json_array() -> None:
    message = build_user_message(["hello", "world"])

    assert json.loads(message) == ["hello", "world"]


def test_parse_translation_response_happy_path() -> None:
    raw = json.dumps(["hola", "mundo"])

    result = parse_translation_response(raw, expected_count=2)

    assert result == ["hola", "mundo"]


def test_parse_translation_response_strips_markdown_fence() -> None:
    raw = "```json\n" + json.dumps(["hola"]) + "\n```"

    result = parse_translation_response(raw, expected_count=1)

    assert result == ["hola"]


def test_parse_translation_response_invalid_json_raises() -> None:
    with pytest.raises(TranslationError, match="JSON valido"):
        parse_translation_response("esto no es json", expected_count=1)


def test_parse_translation_response_wrong_type_raises() -> None:
    with pytest.raises(TranslationError, match="array JSON de strings"):
        parse_translation_response(json.dumps({"text": "hola"}), expected_count=1)


def test_parse_translation_response_wrong_count_raises() -> None:
    with pytest.raises(TranslationError, match="1 lineas, se esperaban 2"):
        parse_translation_response(json.dumps(["hola"]), expected_count=2)
