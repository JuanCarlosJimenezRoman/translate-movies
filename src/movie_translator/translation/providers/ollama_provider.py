"""Proveedor de traduccion sobre un modelo local servido por Ollama.

Requiere el extra 'translation-ollama' (uv sync --extra translation-ollama)
y tener Ollama corriendo localmente (ollama serve) con el modelo descargado
(ollama pull <modelo>). Sin costo por uso, pero necesita hardware suficiente
para correr el modelo con buena calidad.
"""

from __future__ import annotations

import os

import httpx

from movie_translator.translation.providers.base import TranslationProvider
from movie_translator.translation.providers.errors import TranslationError
from movie_translator.translation.providers.prompt import (
    build_system_prompt,
    build_user_message,
    parse_translation_response,
)

DEFAULT_MODEL = "llama3.1"
DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_TIMEOUT_SECONDS = 120.0


class OllamaTranslationProvider(TranslationProvider):
    def __init__(
        self,
        *,
        model: str | None = None,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        self._model = model or os.environ.get("TRANSLATION_OLLAMA_MODEL", DEFAULT_MODEL)
        self._base_url = (
            base_url or os.environ.get("TRANSLATION_OLLAMA_BASE_URL", DEFAULT_BASE_URL)
        ).rstrip("/")
        self._timeout = timeout

    def translate(
        self,
        lines: list[str],
        *,
        source_language: str,
        target_language: str,
        glossary: dict[str, str],
        speakers: dict[str, str] | None = None,
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
            response = httpx.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": self._model,
                    "stream": False,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": build_user_message(lines, speakers)},
                    ],
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise TranslationError(
                f"Fallo llamando a Ollama en {self._base_url} (modelo '{self._model}'): {exc}. "
                "Verifica que 'ollama serve' este corriendo y que el modelo este descargado "
                "('ollama pull " + self._model + "')."
            ) from exc

        raw_text = response.json().get("message", {}).get("content", "")
        return parse_translation_response(raw_text, expected_count=len(lines))
