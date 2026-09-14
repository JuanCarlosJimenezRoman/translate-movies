"""Glosario persistente por proyecto (ver docs/ARCHITECTURE.md, seccion 6).

Termino -> traduccion ya establecida, para mantener consistencia a lo largo
de toda la pelicula (no solo dentro de una escena). Se pasa como contexto en
cada llamada al proveedor de traduccion (ver core/pipeline/translation.py).

Nota (Fase 1): el glosario se lee y se vuelve a guardar en cada corrida,
pero todavia no se actualiza automaticamente a partir de lo que el
proveedor traduce -- eso queda para cuando haya contexto de personaje/escena
(Fase 2). Por ahora es un archivo que un humano puede editar a mano entre
corridas para fijar como debe traducirse un termino recurrente.
"""

from __future__ import annotations

import json
from pathlib import Path

GLOSSARY_FILENAME = "glossary.json"


def load_glossary(path: Path) -> dict[str, str]:
    """Carga el glosario del proyecto. Si todavia no existe, devuelve uno vacio."""
    if not path.exists():
        return {}
    return dict(json.loads(path.read_text(encoding="utf-8")))


def save_glossary(glossary: dict[str, str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(glossary, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
