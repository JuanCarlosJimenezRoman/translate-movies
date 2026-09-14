"""Tests de los proveedores de traduccion concretos y del factory get_provider.

Los SDKs de Anthropic/OpenAI/httpx se mockean: no se hace ninguna llamada de
red real. Se verifica la logica propia (armado de la llamada, parseo de la
respuesta, manejo de errores), no los SDKs en si.
"""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import ClassVar

import httpx
import pytest

import movie_translator.translation.providers.anthropic_provider as anthropic_provider_module
import movie_translator.translation.providers.ollama_provider as ollama_provider_module
import movie_translator.translation.providers.openai_provider as openai_provider_module
from movie_translator.translation.providers import TranslationError, get_provider
from movie_translator.translation.providers.anthropic_provider import (
    AnthropicTranslationProvider,
)
from movie_translator.translation.providers.ollama_provider import OllamaTranslationProvider
from movie_translator.translation.providers.openai_provider import OpenAITranslationProvider

# -- Anthropic ------------------------------------------------------------------


class _FakeAnthropicMessages:
    last_create_kwargs: ClassVar[dict] = {}
    response_text: ClassVar[str] = json.dumps(["hola"])

    def create(self, **kwargs: object) -> SimpleNamespace:
        _FakeAnthropicMessages.last_create_kwargs = kwargs
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text=_FakeAnthropicMessages.response_text)]
        )


class _FakeAnthropicClient:
    last_init_kwargs: ClassVar[dict] = {}

    def __init__(self, **kwargs: object) -> None:
        _FakeAnthropicClient.last_init_kwargs = kwargs
        self.messages = _FakeAnthropicMessages()


def test_anthropic_provider_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(TranslationError, match="ANTHROPIC_API_KEY"):
        AnthropicTranslationProvider()


def test_anthropic_provider_translates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(anthropic_provider_module.anthropic, "Anthropic", _FakeAnthropicClient)
    provider = AnthropicTranslationProvider(api_key="test-key", model="claude-test")

    result = provider.translate(
        ["hello"], source_language="en", target_language="es", glossary={"x": "y"}
    )

    assert result == ["hola"]
    assert _FakeAnthropicClient.last_init_kwargs == {"api_key": "test-key"}
    assert _FakeAnthropicMessages.last_create_kwargs["model"] == "claude-test"
    assert "en" in _FakeAnthropicMessages.last_create_kwargs["system"]


def test_anthropic_provider_empty_lines_short_circuits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(anthropic_provider_module.anthropic, "Anthropic", _FakeAnthropicClient)
    provider = AnthropicTranslationProvider(api_key="test-key")

    assert provider.translate([], source_language="en", target_language="es", glossary={}) == []


def test_anthropic_provider_wraps_api_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    class _RaisingMessages:
        def create(self, **kwargs: object) -> None:
            raise RuntimeError("503 overloaded")

    class _RaisingClient:
        def __init__(self, **kwargs: object) -> None:
            self.messages = _RaisingMessages()

    monkeypatch.setattr(anthropic_provider_module.anthropic, "Anthropic", _RaisingClient)
    provider = AnthropicTranslationProvider(api_key="test-key")

    with pytest.raises(TranslationError, match="503 overloaded"):
        provider.translate(["hello"], source_language="en", target_language="es", glossary={})


# -- OpenAI -----------------------------------------------------------------


class _FakeOpenAICompletions:
    last_create_kwargs: ClassVar[dict] = {}
    response_text: ClassVar[str] = json.dumps(["hola"])

    def create(self, **kwargs: object) -> SimpleNamespace:
        _FakeOpenAICompletions.last_create_kwargs = kwargs
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=_FakeOpenAICompletions.response_text)
                )
            ]
        )


class _FakeOpenAIClient:
    last_init_kwargs: ClassVar[dict] = {}

    def __init__(self, **kwargs: object) -> None:
        _FakeOpenAIClient.last_init_kwargs = kwargs
        self.chat = SimpleNamespace(completions=_FakeOpenAICompletions())


def test_openai_provider_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(TranslationError, match="OPENAI_API_KEY"):
        OpenAITranslationProvider()


def test_openai_provider_translates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(openai_provider_module.openai, "OpenAI", _FakeOpenAIClient)
    provider = OpenAITranslationProvider(api_key="test-key", model="gpt-test")

    result = provider.translate(
        ["hello"], source_language="en", target_language="es", glossary={}
    )

    assert result == ["hola"]
    assert _FakeOpenAICompletions.last_create_kwargs["model"] == "gpt-test"


# -- Ollama -------------------------------------------------------------------


def test_ollama_provider_translates(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    def fake_post(url: str, *, json: object, timeout: float) -> SimpleNamespace:
        captured["url"] = url
        captured["json"] = json
        return SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {"message": {"content": '["hola"]'}},
        )

    monkeypatch.setattr(ollama_provider_module.httpx, "post", fake_post)
    provider = OllamaTranslationProvider(model="llama-test", base_url="http://localhost:11434")

    result = provider.translate(
        ["hello"], source_language="en", target_language="es", glossary={}
    )

    assert result == ["hola"]
    assert captured["url"] == "http://localhost:11434/api/chat"
    assert captured["json"]["model"] == "llama-test"


def test_ollama_provider_wraps_connection_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_post(*args: object, **kwargs: object) -> None:
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(ollama_provider_module.httpx, "post", fake_post)
    provider = OllamaTranslationProvider(model="llama-test")

    with pytest.raises(TranslationError, match="ollama serve"):
        provider.translate(["hello"], source_language="en", target_language="es", glossary={})


# -- Factory (get_provider) ----------------------------------------------------


def test_get_provider_unknown_name_raises() -> None:
    with pytest.raises(TranslationError, match="anthropic, openai, ollama"):
        get_provider("deepseek")


def test_get_provider_anthropic_without_key_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("TRANSLATION_PROVIDER", raising=False)

    with pytest.raises(TranslationError, match="ANTHROPIC_API_KEY"):
        get_provider()


def test_get_provider_reads_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRANSLATION_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(TranslationError, match="OPENAI_API_KEY"):
        get_provider()


def test_get_provider_explicit_name_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRANSLATION_PROVIDER", "openai")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(TranslationError, match="ANTHROPIC_API_KEY"):
        get_provider("anthropic")
