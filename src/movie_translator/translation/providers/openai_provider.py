"""Proveedor de traduccion sobre la API de OpenAI.

Requiere el extra 'translation-openai' (uv sync --extra translation-openai)
y la variable de entorno OPENAI_API_KEY.
"""

from __future__ import annotations

import os

import openai

from movie_translator.translation.providers.base import TranslationProvider
from movie_translator.translation.providers.errors import TranslationError
from movie_translator.translation.providers.prompt import (
    build_system_prompt,
    build_user_message,
    parse_translation_response,
)

DEFAULT_MODEL = "gpt-4o-mini"


class OpenAITranslationProvider(TranslationProvider):
    def __init__(self, *, api_key: str | None = None, model: str | None = None) -> None:
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise TranslationError(
                "Falta OPENAI_API_KEY. Definela como variable de entorno, o pasa "
                "api_key explicitamente."
            )
        self._client = openai.OpenAI(api_key=key)
        self._model = model or os.environ.get("TRANSLATION_OPENAI_MODEL", DEFAULT_MODEL)

    def translate(
        self,
        lines: list[str],
        *,
        source_language: str,
        target_language: str,
        glossary: dict[str, str],
    ) -> list[str]:
        if not lines:
            return []

        system_prompt = build_system_prompt(
            source_language=source_language,
            target_language=target_language,
            line_count=len(lines),
            glossary=glossary,
        )

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": build_user_message(lines)},
                ],
            )
        except Exception as exc:
            raise TranslationError(f"Fallo llamando a OpenAI ({self._model}): {exc}") from exc

        raw_text = response.choices[0].message.content or ""
        return parse_translation_response(raw_text, expected_count=len(lines))
