"""Proveedores de traduccion: interfaz comun + registro por nombre.

El proveedor concreto se elige por configuracion (ver docs/DECISIONES.md),
no queda fijo en el codigo. Cada proveedor concreto se importa solo cuando
se pide (get_provider), asi que instalar el proyecto no obliga a tener
instalados los SDKs de los proveedores que no se van a usar.
"""

from __future__ import annotations

import os
from typing import Any

from movie_translator.translation.providers.base import TranslationProvider
from movie_translator.translation.providers.errors import TranslationError

DEFAULT_PROVIDER_NAME = "anthropic"
PROVIDER_NAMES = ("anthropic", "openai", "ollama")


def get_provider(name: str | None = None, **kwargs: Any) -> TranslationProvider:
    """Instancia un TranslationProvider por nombre.

    Si `name` es None, se usa la variable de entorno TRANSLATION_PROVIDER,
    y si tampoco esta definida, `DEFAULT_PROVIDER_NAME`. `kwargs` se pasan
    al constructor del proveedor concreto (ej. api_key, model).

    Lanza TranslationError si el nombre no es uno de PROVIDER_NAMES, o si el
    paquete del SDK correspondiente no esta instalado.
    """
    provider_name = (name or os.environ.get("TRANSLATION_PROVIDER") or DEFAULT_PROVIDER_NAME).lower()

    if provider_name == "anthropic":
        try:
            from movie_translator.translation.providers.anthropic_provider import (
                AnthropicTranslationProvider,
            )
        except ImportError as exc:
            raise TranslationError(
                "Falta el paquete 'anthropic'. Instala con: "
                "uv sync --extra translation-anthropic"
            ) from exc
        return AnthropicTranslationProvider(**kwargs)

    if provider_name == "openai":
        try:
            from movie_translator.translation.providers.openai_provider import (
                OpenAITranslationProvider,
            )
        except ImportError as exc:
            raise TranslationError(
                "Falta el paquete 'openai'. Instala con: uv sync --extra translation-openai"
            ) from exc
        return OpenAITranslationProvider(**kwargs)

    if provider_name == "ollama":
        try:
            from movie_translator.translation.providers.ollama_provider import (
                OllamaTranslationProvider,
            )
        except ImportError as exc:
            raise TranslationError(
                "Falta el paquete 'httpx'. Instala con: uv sync --extra translation-ollama"
            ) from exc
        return OllamaTranslationProvider(**kwargs)

    raise TranslationError(
        f"Proveedor de traduccion desconocido: {provider_name!r}. "
        f"Opciones: {', '.join(PROVIDER_NAMES)}."
    )


__all__ = [
    "DEFAULT_PROVIDER_NAME",
    "PROVIDER_NAMES",
    "TranslationError",
    "TranslationProvider",
    "get_provider",
]
