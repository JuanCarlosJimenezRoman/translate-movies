"""Errores especificos de los proveedores de traduccion."""

from __future__ import annotations


class TranslationError(RuntimeError):
    """Fallo llamando al proveedor de traduccion, o respuesta invalida/incompleta."""
