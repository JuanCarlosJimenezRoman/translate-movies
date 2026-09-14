"""Construccion del prompt y parseo de la respuesta, compartidos por los
proveedores de traduccion (ver docs/ARCHITECTURE.md, seccion 7)."""

from __future__ import annotations

import json

from movie_translator.translation.providers.errors import TranslationError

SYSTEM_PROMPT_TEMPLATE = """Eres un traductor profesional de dialogos de peliculas, de {source} a {target}. Traduces para subtitulado (y eventualmente doblaje): natural y coloquial, fiel al tono y a la longitud aproximada del original -- no es traduccion literal palabra por palabra.

Reglas:
- Devuelve EXCLUSIVAMENTE un array JSON de strings, con exactamente {n} elementos, en el mismo orden que las lineas de entrada. Sin texto extra, sin explicaciones, sin markdown, sin bloques de codigo.
- Usa estas traducciones ya establecidas para mantener consistencia si el termino vuelve a aparecer:
{glossary}
- El mensaje del usuario puede venir como un array de strings sueltos, o como un array de objetos {{"speaker": "<nombre o null>", "text": "..."}} cuando se conoce que personaje dice cada linea. En ese segundo caso, usa "speaker" solo como contexto para adaptar el dialogo al tono/personalidad de quien habla -- la respuesta sigue siendo SIEMPRE un array plano de {n} strings traducidos, sin el campo speaker, en el mismo orden.
"""


def build_system_prompt(
    *,
    source_language: str,
    target_language: str,
    line_count: int,
    glossary: dict[str, str],
) -> str:
    glossary_text = (
        "\n".join(f'- "{term}" -> "{translation}"' for term, translation in glossary.items())
        or "(vacio por ahora)"
    )
    return SYSTEM_PROMPT_TEMPLATE.format(
        source=source_language,
        target=target_language,
        n=line_count,
        glossary=glossary_text,
    )


def build_user_message(lines: list[str], speakers: dict[str, str] | None = None) -> str:
    """Arma el mensaje de usuario: array de strings, o de objetos con hablante.

    `speakers` (Fase 2, opcional) mapea el indice de cada linea dentro de
    `lines` (como string: "0", "1", ...) al nombre del personaje que la
    dice. Si es None o esta vacio, se manda el formato simple de Fase 1
    (array de strings) sin cambios.
    """
    if not speakers:
        return json.dumps(lines, ensure_ascii=False, indent=2)

    payload = [{"speaker": speakers.get(str(i)), "text": line} for i, line in enumerate(lines)]
    return json.dumps(payload, ensure_ascii=False, indent=2)


def parse_translation_response(raw_text: str, *, expected_count: int) -> list[str]:
    """Parsea la respuesta del modelo: debe ser un array JSON de `expected_count` strings.

    Tolera que el modelo la envuelva en un bloque ```json pese a la
    instruccion de no hacerlo (pasa con cierta frecuencia).
    """
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.removeprefix("json")
        text = text.strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise TranslationError(
            f"El proveedor no devolvio JSON valido: {exc}. Respuesta cruda: {raw_text!r}"
        ) from exc

    if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
        raise TranslationError(f"Se esperaba un array JSON de strings, se recibio: {raw_text!r}")

    if len(data) != expected_count:
        raise TranslationError(
            f"El proveedor devolvio {len(data)} lineas, se esperaban {expected_count}."
        )

    return data
