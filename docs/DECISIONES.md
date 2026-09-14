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
| 2026-09-13 | Video fuente | No se copia a `projects/<nombre>/source/`. `project.json` guarda la ruta absoluta del original y el pipeline lee de ahi, para no duplicar espacio en archivos de decenas de GB. `source/` queda reservado para un futuro flag `--copy-source` opcional. |
| 2026-09-13 | Modelo Whisper (Fase 1) | `small` por defecto en CPU (buen balance calidad/velocidad), configurable por `--model` en el CLI (`tiny`/`base`/`small`/...). Cuantizacion `int8` para acelerar en CPU. |
| 2026-09-13 | Python del proyecto | 3.11 via `uv python install` (no el 3.10 del sistema), porque onnxruntime (dependencia de faster-whisper) no publica wheels para 3.10. |
| 2026-09-13 | Extras de `pyproject.toml` | `faster-whisper`, `av`, `cython` y `srt` pasaron de extras opcionales a `dependencies` base: son parte del uso normal del CLI desde la Fase 1, no features futuras. Motivo: Juan corrio `uv sync` (sin `--extra transcription`) despues de haberlo usado con el extra, y `uv sync` reconcilia el venv exactamente al conjunto de extras pedido en esa llamada, desinstalando lo demas -- eso rompio `movie-translator new`/`transcribe` en su maquina. Solo quedan como extras las cosas genuinamente opcionales: que proveedor de traduccion usar, y las dependencias pesadas de fases futuras. |

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

| 2026-09-14 | Interfaz de traduccion | `TranslationProvider.translate(lines, source_language, target_language, glossary) -> list[str]`: traduce lotes de lineas (no linea por linea), devuelve el mismo numero de lineas en el mismo orden. Los tres proveedores (Anthropic/OpenAI/Ollama) devuelven un array JSON de strings -- formato facil de validar y parsear igual sin importar el proveedor. |
| 2026-09-14 | Tamano de lote de traduccion | 40 lineas consecutivas por llamada por defecto (`--batch-size`), como aproximacion a "agrupar por escena" (todavia no hay deteccion real de escenas). |

## Limitaciones conocidas

- **El glosario no se actualiza automaticamente todavia**: `translation/glossary.json`
  se lee y se le vuelve a pasar al proveedor en cada lote (para consistencia),
  pero ningun proveedor extrae terminos nuevos de sus propias traducciones
  todavia -- eso requiere mas contexto de personaje/escena (Fase 2). Por ahora
  es un archivo editable a mano entre corridas.
- **`confidence` es por ventana de decodificacion, no por linea**: Whisper
  (y por lo tanto faster-whisper) calcula `avg_logprob` (de donde sacamos
  `confidence`) una vez por cada ventana de audio que decodifica (~30s), no
  por cada segmento/linea de texto que arroja esa ventana. Si varias lineas
  salen de la misma ventana, todas comparten exactamente el mismo valor de
  confianza. Se confirmo esto con un clip real (Juan, fuera del entorno
  remoto): 6 segmentos consecutivos con texto distinto, con el mismo
  `confidence` a 16 decimales. No es un bug de nuestro codigo, es como
  Whisper expone esta metrica. Si mas adelante se necesita confianza real
  por linea (por ejemplo para marcar que lineas revisar a mano antes de
  traducir), la forma correcta es pedir `word_timestamps=True` y promediar
  la probabilidad por palabra dentro de cada segmento, en vez de usar
  `avg_logprob` tal cual. No se implemento todavia (Fase 1 no lo necesita).

## Bloqueos de entorno detectados

- **Descarga de modelos de Whisper bloqueada desde el entorno remoto de Claude**: el proxy de red de esta sesion remota devuelve 403 al intentar llegar a `huggingface.co` (de donde faster-whisper descarga los pesos), aunque `pypi.org` si es alcanzable. La transcripcion esta implementada y probada con mocks (43 tests), pero una corrida real con un modelo de verdad hay que hacerla desde una terminal normal en tu maquina (fuera de este entorno remoto), o descargando el modelo a mano y apuntando `--models-dir` a esa carpeta.

Este documento se actualiza según se resuelvan preguntas o aparezcan nuevas.
