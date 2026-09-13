# Decisiones — Movie Translator

## Tomadas

| Fecha | Decisión | Detalle |
|---|---|---|
| 2026-09-13 | Estructura del repo | `src/movie_translator/` como paquete único (src layout), en vez de módulos sueltos bajo `src/` directamente. |
| 2026-09-13 | Gestor de Python | `uv` para entorno, dependencias y lockfile. |
| 2026-09-13 | Proveedor de traducción (Fase 1) | No se fija en código. `TranslationProvider` es una interfaz; el proveedor concreto (Anthropic / OpenAI / Ollama) se elige por configuración. |
| 2026-09-13 | Hardware (Fase 1) | Solo CPU. La Fase 1 (extracción + transcripción + traducción + subtítulos) no depende de GPU. |
| 2026-09-13 | Patrón de proveedores | `translation/` y `tts/` usan la misma forma: interfaz base + carpeta `providers/`, en vez de estructuras distintas para cada módulo. |
| 2026-09-13 | Cola de jobs (inicial) | SQLite + workers async, sin Redis/Airflow, hasta que de verdad haga falta escalar. |

## Pendientes (bloquean o afectan fases futuras)

- **Clonación de voz vs. voces genéricas** (bloquea diseño de Fase 3): ¿el TTS
  debe clonar la voz del actor original o usar un catálogo de voces por
  personaje? Cambia el proveedor de TTS a implementar y tiene implicaciones de
  uso/derechos que conviene decidir explícitamente antes de escribir código de
  la Fase 3.
- **Proveedor de traducción final**: hoy queda como configuración (ver tabla
  de arriba). Se puede decidir más adelante sin bloquear la Fase 1, pero hay
  que probar al menos uno de verdad para cerrar esa fase.
- **Gestión de modelos** (`models/`): falta definir cómo se versionan y
  descargan los pesos de Whisper/Demucs/TTS (manifest, descarga bajo demanda),
  considerando el crecimiento de espacio en disco ya identificado.
- **Extraer subtítulos/pistas ya existentes en el MKV**: evaluar si conviene
  usar una pista de subtítulos en inglés ya embebida como atajo en vez de
  correr Whisper siempre.

Este documento se actualiza según se resuelvan preguntas o aparezcan nuevas.
