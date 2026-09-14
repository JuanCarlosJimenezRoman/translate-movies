"""Glosario persistente por proyecto."""

from movie_translator.translation.glossary.glossary import (
    GLOSSARY_FILENAME,
    load_glossary,
    save_glossary,
)

__all__ = ["GLOSSARY_FILENAME", "load_glossary", "save_glossary"]
