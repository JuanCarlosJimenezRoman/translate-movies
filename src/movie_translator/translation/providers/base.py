"""Interfaz comun para los proveedores de traduccion.

Ver docs/ARCHITECTURE.md, seccion 7: el proveedor concreto (Anthropic,
OpenAI, Ollama...) se elige por configuracion, no queda fijo en el codigo
(ver docs/DECISIONES.md). Todos implementan esta misma interfaz.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class TranslationProvider(ABC):
    """Traduce lotes de lineas de dialogo, con el glosario del proyecto como contexto.

    No se traduce linea por linea de forma aislada (docs/ARCHITECTURE.md,
    seccion 7): quien llama agrupa lineas consecutivas en lotes (ver
    core/pipeline/translation.py) para darle contexto narrativo real al
    proveedor.
    """

    @abstractmethod
    def translate(
        self,
        lines: list[str],
        *,
        source_language: str,
        target_language: str,
        glossary: dict[str, str],
        speakers: dict[str, str] | None = None,
    ) -> list[str]:
        """Traduce `lines` y devuelve la misma cantidad de lineas, en el mismo orden.

        `glossary` es termino -> traduccion ya establecida en llamadas
        anteriores de este proyecto, para mantener consistencia
        (docs/ARCHITECTURE.md, seccion 6).

        `speakers` (Fase 2, opcional) asocia cada linea de `lines` con el
        personaje que la dice, para que la traduccion se adapte a su tono en
        vez de tratar cada linea como texto suelto (docs/ROADMAP.md, Fase 2).
        Las claves son el indice de la linea dentro de `lines` como string
        ("0", "1", ...) y los valores el nombre del personaje; una linea sin
        hablante identificado (diarizacion sin resultado, o proyecto sin
        diarizar todavia) simplemente no aparece en el dict. None o {}
        significa "sin contexto de personaje" (equivalente a la Fase 1).

        Debe lanzar TranslationError si el proveedor falla, o si la
        respuesta no tiene exactamente `len(lines)` elementos.
        """
