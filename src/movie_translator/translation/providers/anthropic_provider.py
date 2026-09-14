"""Proveedor de traduccion sobre la API de Anthropic (Claude).

Requiere el extra 'translation-anthropic' (uv sync --extra translation-anthropic)
y la variable de entorno ANTHROPIC_API_KEY.
"""

from __future__ import annotations

import os

import anthropic

from movie_translator.translation.providers.base import TranslationProvider
from movie_translator.translation.providers.errors import TranslationError
from movie_translator.translation.providers.prompt import (
    build_system_prompt,
    build_user_message,
    parse_translation_response,
)

# Verifica el modelo vigente en https://docs.claude.com/en/docs/about-claude/models
# antes de traducir peliculas completas: los IDs de modelo cambian con el tiempo.
DEFAULT_MODEL = "claude-sonnet-4-5-20250929"
MAX_TOKENS = 8192


class AnthropicTranslationProvider(TranslationProvider):
    def __init__(self, *, api_key: str | None = None, model: str | None = None) -> None:
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise TranslationError(
                "Falta ANTHROPIC_API_KEY. Definela como variable de entorno, o pasa "
                "api_key explicitamente."
            )
        self._client = anthropic.Anthropic(api_key=key)
        self._model = model or os.environ.get("TRANSLATION_ANTHROPIC_MODEL", DEFAULT_MODEL)

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
            response = self._client.messages.create(
                model=self._model,
                max_tokens=MAX_TOKENS,
                system=system_prompt,
                messages=[{"role": "user", "content": build_user_message(lines)}],
            )
        except Exception as exc:
            raise TranslationError(f"Fallo llamando a Anthropic ({self._model}): {exc}") from exc

        raw_text = "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )
        return parse_translation_response(raw_text, expected_count=len(lines))
