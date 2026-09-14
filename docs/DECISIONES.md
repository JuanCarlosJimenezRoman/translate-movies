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
| 2026-09-14 | VAD de transcripcion mas permisivo | `transcribe_audio()` baja los parametros del VAD de faster-whisper (`threshold` 0.5->0.2, `min_silence_duration_ms` 2000->1000) en vez de usar los defaults de la libreria. Motivo: con los defaults, canciones (voz cantada + musica de fondo) se clasifican como "no es voz" y se descartan enteras sin que Whisper llegue a intentarlas -- confirmado con `projects/prueba` (cancion de ~4 min): con defaults solo salian 6 de 35 segmentos reales (11-37s de 245s). El VAD sigue activo (no se desactiva del todo) para no perder la proteccion contra alucinaciones en silencios reales de dialogo. Ver "Limitaciones conocidas" mas abajo: esto ayuda pero no recupera una cancion completa. |

| 2026-09-14 | Formato de `speakers.json` (Fase 2) | Objeto completo desde el arranque: `{"SPEAKER_NN": {"character": ..., "voice": null}}`, coincidiendo con el ejemplo que ya tenia `ARCHITECTURE.md` seccion 6. `voice` queda en `null` hasta Fase 3 (TTS); evita migrar el archivo mas adelante. |
| 2026-09-14 | Asignacion de hablante a segmento (Fase 2) | Mayor solapamiento de tiempo entre el segmento de Whisper y los turnos de pyannote (regla estandar). Sin solapamiento con ningun turno, `speaker` queda en `None` -- no se inventa un hablante; la linea simplemente queda sin contexto de personaje en la traduccion. Implementado en `transcription/diarization/turns.py` (`assign_speakers`), sin ninguna dependencia de pyannote instalado (funcion pura, testeada aparte). |
| 2026-09-14 | Checkpoint humano para nombrar hablantes (Fase 2) | Prompt interactivo (`movie-translator name-speakers`): recorre cada `SPEAKER_NN` detectado, muestra hasta 3 lineas de ejemplo de ese hablante y pide el nombre con `typer.prompt` (default = nombre actual o la etiqueta cruda). Se puede re-correr para corregir un nombre sin perder los demas. Se descarto la alternativa de editar `speakers.json` a mano por peor UX, sin ganar simplicidad real de implementacion. |
| 2026-09-14 | Interfaz de `TranslationProvider.translate()` (Fase 2) | Se agrega un parametro opcional `speakers: dict[str, str] \| None`. Las claves son el indice de la linea dentro del lote como string (`"0"`, `"1"`, ...), los valores el nombre del personaje que la dice; una linea sin hablante no aparece en el dict. `None`/`{}` es identico al comportamiento de Fase 1 (backward-compatible, ningun test viejo se rompio por el tipo -- si por la firma: los proveedores fake de los tests tuvieron que aceptar el kwarg nuevo). Cuando hay `speakers`, `build_user_message` cambia el payload de un array de strings a un array de objetos `{"speaker": ..., "text": ...}`; la respuesta esperada no cambia (sigue siendo un array plano de N strings). Se prefirio esto sobre agrupar por escena real porque agrupar por escena es un cambio de pipeline mas grande y no habia deteccion de escenas todavia -- se puede migrar despues sin romper la interfaz de nuevo (el batch de N lineas seguiria siendo un caso particular). |
| 2026-09-14 | Hardware (Fase 2) | CPU, igual que Fase 1. La migracion real a GPU (diarizacion incluida) sigue siendo Fase 7 del roadmap; no se adelanta sin necesidad concreta. |

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
| 2026-09-14 | Etapa `subtitles` en el pipeline | Se agrego `StageName.SUBTITLES` entre `TRANSLATION` y `TTS` en `STAGE_ORDER`. Los `project.json` viejos que no tienen esa clave en `stages` siguen cargando bien: se tratan como `pending` (`Project.pending_stage`/`progress_lines` usan `.get()` con default). |
| 2026-09-14 | Subtitulos: no truncar ni acortar texto para "cumplir" las reglas | `subtitles/generate.py` nunca corta el texto traducido para que quepa en el maximo de lineas/CPS -- eso cambiaria la traduccion sin que nadie lo revise. En cambio: envuelve el texto (puede terminar en mas lineas de las recomendadas), extiende cues mas cortos que 1s hasta el minimo sin invadir el siguiente cue, y devuelve una lista de warnings (cue, timestamp, regla incumplida) que el CLI muestra para revision manual. Coincide con lo que pide `ARCHITECTURE.md` seccion 8 ("marca los cues que no cumplen para revision"). |
| 2026-09-14 | Nombre del archivo de subtitulos | `subtitles/<target_language>.srt` (ej. `es.srt`), no un nombre fijo tipo `spanish.srt` -- se deriva del codigo de idioma del proyecto para que funcione igual sin importar el par de idiomas. |

## Limitaciones conocidas

- **El glosario no se actualiza automaticamente todavia**: `translation/glossary.json`
  se lee y se le vuelve a pasar al proveedor en cada lote (para consistencia),
  pero ningun proveedor extrae terminos nuevos de sus propias traducciones
  todavia -- eso requiere mas contexto de personaje/escena (Fase 2). Por ahora
  es un archivo editable a mano entre corridas.
- **El VAD permisivo no recupera canciones completas, solo mejora el caso**:
  se probo bajar `threshold` hasta 0.05 sobre el mismo clip de `projects/prueba`
  y ni asi se recupero el audio completo (maximo ~78s de 245s, y de forma no
  monotona: 0.1 dio mejor cobertura que 0.05). Para audio con canto sostenido
  sobre musica, la unica forma confirmada de transcribirlo completo es
  `vad_filter=False` (ver `transcribe_audio(..., vad_parameters=...)` -- hoy
  no hay forma de desactivar el VAD del todo sin tocar el codigo, no hay flag
  de CLI para eso). Si en el futuro aparecen escenas musicales dentro de una
  pelicula real (no solo el clip de prueba), esto va a necesitar resolverse
  de verdad -- por ejemplo separando la pista de musica (Fase 4, `demucs`)
  antes de transcribir esa escena, en vez de solo afinar el VAD.
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

| 2026-09-14 | `.env` no se cargaba nunca (fix, no era una decision de diseno) | `python-dotenv` estaba declarado como dependencia desde el arranque del proyecto pero ningun archivo lo importaba -- `HF_TOKEN`/`ANTHROPIC_API_KEY`/etc en `.env` no llegaban a `os.environ` salvo que se exportaran a mano en la shell. Se agrego `load_dotenv()` al principio de `apps/cli/main.py` (no-op si no existe `.env`, no pisa variables ya exportadas en la shell). Encontrado al intentar validar diarizacion con el `HF_TOKEN` que Juan ya habia puesto en `.env`. |

## Bloqueos de entorno detectados

- **La descarga de modelos "gated" de HuggingFace tambien esta bloqueada desde el puente a la maquina de Juan (`device_bash`), no solo desde el entorno remoto de Claude**: se probo `curl https://huggingface.co` desde `device_bash` (que corre en una VM Linux aislada en la maquina de Juan, no en el entorno remoto original) y da el mismo `403` de proxy que ya se conocia del lado remoto. Tambien se probo `curl http://localhost:11434` (Ollama) desde ahi y da "connection refused" -- la VM aislada de `device_bash` no comparte la red del propio Windows de Juan, asi que ni siquiera un Ollama corriendo en su maquina es alcanzable desde ese puente. **Conclusion**: correr `movie-translator diarize` (pyannote descargando modelos) y `movie-translator translate --provider ollama` de verdad, con red real, tiene que hacerse desde una PowerShell normal de Juan -- ningun acceso mediado por Claude (ni el entorno remoto, ni el puente a su maquina) sirve para esto. Confirmado 2026-09-14 al intentar validar diarizacion con audio real.
- **Descarga de modelos de Whisper bloqueada desde el entorno remoto de Claude**: el proxy de red de esta sesion remota devuelve 403 al intentar llegar a `huggingface.co` (de donde faster-whisper descarga los pesos), aunque `pypi.org` si es alcanzable. La transcripcion esta implementada y probada con mocks (43 tests), pero una corrida real con un modelo de verdad hay que hacerla desde una terminal normal en tu maquina (fuera de este entorno remoto), o descargando el modelo a mano y apuntando `--models-dir` a esa carpeta.
- **`.venv` en la carpeta del proyecto es de Juan (Windows), no de Claude**: un venv de Python no es portable entre SO (binarios/paths distintos). Cuando Claude opera sobre esta carpeta desde su propio acceso (que corre en un Linux separado, aunque vea los mismos archivos), correr `uv sync`/`uv run` sin cuidado intenta reemplazar el `.venv` de Windows por uno de Linux -- a veces se queda a medio borrar (`Operation not permitted` en archivos sueltos como `.venv/.gitignore`) y deja el entorno de Juan roto. Ya paso una vez (2026-09-14) y se corrigio borrando el `.venv` a medias y dejando que Juan lo regenere solo. **Regla para sesiones futuras de Claude**: nunca tocar `.venv` en esta carpeta; usar `export UV_PROJECT_ENVIRONMENT=~/venvs/translate-movies-linux` (ruta fuera del mount, dentro del propio entorno de Claude) antes de cualquier `uv sync`/`uv run` propio, para que el venv de Linux de Claude y el `.venv` de Windows de Juan nunca se pisen.

- **`.venv` ya NO es un directorio real: es un symlink roto a una sesion vieja de Claude** (encontrado 2026-09-14, sesion de Fase 2): `ls -la .venv` muestra `.venv -> /sessions/rcw-015bnhnqceyfxjlahuybz5jq/venvs/translate-movies`, un path de sandbox de OTRA sesion de Claude (no un path de Windows). Eso significa que en algun momento una sesion anterior de Claude creo `.venv` como symlink en vez de dejarlo como el venv real de Juan -- contradice la regla de "nunca tocar `.venv`" de mas arriba, que asumia que seguia siendo el venv real de Windows. **Efecto practico para Claude**: `pytest` (sin argumentos especificos, o incluso con `tests/` explicito) falla con `PermissionError` al escanear la raiz del repo buscando `conftest.py`, porque intenta hacer `stat` de ese symlink roto y el mount lo deniega. Poner `UV_PROJECT_ENVIRONMENT` en otro lado (regla de mas arriba) NO alcanza para evitar esto -- el problema es escanear el directorio raiz, no donde vive el venv de Claude. **Workaround usado**: copiar el repo (con `rsync -a --exclude='.venv' --exclude='.git' --exclude='/projects' --exclude='/models' --exclude='__pycache__' ...` -- ojo con anclar `/models` y `/projects` con `/` inicial, si no tambien excluye `core/models`) a un scratch dir fuera del mount, y correr `uv sync`/`pytest`/`ruff`/`mypy` ahi. **Para Juan**: si tu `.venv` local en Windows dejo de funcionar en algun momento reciente, es probablemente por esto -- valdria la pena que folder lo revises vos mismo desde tu maquina (`Get-Item .venv` en PowerShell) y lo borres/regeneres si hace falta; ninguna sesion de Claude lo va a tocar sin que lo pidas explicitamente.

Este documento se actualiza según se resuelvan preguntas o aparezcan nuevas.
