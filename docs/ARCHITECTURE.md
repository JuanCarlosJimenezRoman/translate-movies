# Arquitectura — Movie Translator

Este documento es la referencia de arquitectura del proyecto. Se basa en el
planteamiento original (`proyecto.txt`) e incorpora los ajustes de la revisión
inicial (`docs/DECISIONES.md`). Se actualiza a medida que el proyecto avanza;
si una decisión cambia, se edita aquí, no se abre un documento nuevo.

## 1. Objetivo

Pasar de `movie.mkv` a `movie.es.mkv` con subtítulos y, más adelante, doblaje,
mediante un pipeline de IA dividido en etapas independientes y reanudables.

## 2. Principio rector

No procesar una película como caja negra. Cada etapa (extracción, separación,
transcripción, diarización, traducción, TTS, mezcla, encoding) se ejecuta,
registra su resultado y su estado por separado, para poder:

- reanudar sin repetir trabajo ya hecho (una transcripción de 2 horas no se
  vuelve a correr porque falló la traducción),
- reintentar solo la etapa que falló,
- inspeccionar y corregir manualmente un resultado intermedio (por ejemplo,
  reasignar un hablante mal identificado) antes de seguir.

## 3. Pipeline de extremo a extremo

```
movie.mkv
   |
   v
[FFmpeg] extraer audio/video
   |
   v
audio original ---------------------------+
   |                                       |
   v                                       |
[Demucs] separacion de fuentes             |
   |                                       |
   +-- vocals --+                          |
   |            v                          |
   |      [faster-whisper] transcripcion   |
   |            |                          |
   |            v                          |
   |      [pyannote] diarizacion           |
   |            |                          |
   |            v                          |
   |      speaker timeline (JSON)          |
   |            |                          |
   |     (checkpoint humano: nombrar       |
   |      hablantes, ver seccion 6)        |
   |            |                          |
   |            v                          |
   |      [Translation Provider]           |
   |      + glosario del proyecto          |
   |            |                          |
   |            v                          |
   |      script traducido (JSON)          |
   |            |                          |
   |            +--> [Subtitles] -> movie.es.srt   (** entregable Fase 1 **)
   |            |
   |            v
   |      [TTS Provider] genera voces
   |            |
   |            v
   |      [Sync] ajusta duracion vs. timestamp original
   |            |                          |
   +-- music ---+                          |
   +-- effects -+                          |
                v
          [Audio Mixer] voces + musica + efectos
                |
                v
          [FFmpeg] multiplexado final
                |
                v
          movie_es.mkv (video + audio ES + audio original + subtitulos)
```

Puntos importantes de este diagrama respecto al boceto original:

- Hay un **checkpoint humano explícito** después de la diarización (sección 6):
  asignar nombres a `SPEAKER_01`, `SPEAKER_02`... antes de traducir. No es un
  paso automático que se nos haya olvidado diseñar; es intencional, porque un
  error de diarización sin corregir contamina traducción, voces y mezcla.
- Hay un **loop de sincronizacion** entre TTS y traduccion (seccion 9): si el
  audio generado no cabe en el hueco de tiempo original, se vuelve a pedir al
  proveedor de traducción una versión más corta, no solo se acelera el audio.

## 4. Estructura de carpetas

```
translate-movies/
├── apps/
│   ├── cli/                    # movie-translator (Typer)
│   └── api/                    # FastAPI, se añade en Fase 6
├── src/movie_translator/       # paquete instalable (src layout)
│   ├── core/
│   │   ├── config/             # settings, carga de .env
│   │   ├── models/             # modelos Pydantic (Project, Segment, Job...)
│   │   ├── pipeline/           # orquestador de etapas
│   │   └── jobs/               # cola de jobs (ver seccion 7)
│   ├── media/
│   │   ├── ffmpeg/             # wrappers de extraccion/encoding
│   │   ├── audio/
│   │   └── video/
│   ├── transcription/
│   │   ├── whisper/            # faster-whisper
│   │   └── diarization/        # pyannote.audio
│   ├── translation/
│   │   ├── providers/          # anthropic.py, openai.py, ollama.py...
│   │   └── glossary/           # glosario persistente por proyecto (seccion 6)
│   ├── subtitles/               # generacion/formato de .srt (seccion 5)
│   ├── tts/
│   │   └── providers/          # local.py, elevenlabs.py, openai.py...
│   └── mixing/                 # Demucs + mezcla final
├── models/                      # pesos descargados (gitignored)
├── projects/                    # una carpeta por pelicula (gitignored, seccion 5)
├── fixtures/                    # clips cortos (2-5 min) para desarrollo/tests
├── tests/
├── docs/
│   ├── ARCHITECTURE.md          # este documento
│   ├── ROADMAP.md               # fases y checklist
│   └── DECISIONES.md            # decisiones tomadas y pendientes
├── pyproject.toml
└── README.md
```

Cambio respecto al boceto original: en vez de `src/translation/{local,openai,anthropic,ollama}`
y `src/tts/{local,providers}` (estructuras distintas para dos cosas que son el
mismo patrón), ambos módulos usan la misma forma: una interfaz base
(`TranslationProvider`, `TTSProvider`) y una carpeta `providers/` con una
implementación por proveedor. Un solo patrón que se aprende una vez y se repite.

## 5. Proyecto por película (`projects/<nombre>/`)

```
projects/matrix/
├── source/          # reservado para un futuro flag --copy-source (ver mas abajo)
├── audio/{original,vocals,music,effects}.wav
├── transcription/{original.json, speakers.json}
├── translation/{draft.json, final.json, glossary.json}
├── voices/speaker_01.wav ...
├── subtitles/es.srt      # <target_language>.srt (implementado solo el traducido; original.srt queda para el futuro)
├── output/matrix_es.mkv
└── project.json
```

El video original **no se copia** a `source/`: `project.json` guarda su ruta
absoluta (`source_file`) y toda etapa que lo necesite lee directamente de ahi.
Copiar peliculas de decenas de GB al crear cada proyecto agravaria el
problema de espacio que se describe mas abajo; `source/` queda reservado
para cuando se agregue un flag `--copy-source` opcional, para quien
necesite un proyecto portable (ej. para moverlo a otra maquina).

`project.json` guarda el estado de cada etapa (`pending` / `running` /
`completed` / `failed`) y es lo que permite al CLI mostrar algo como:

```
✓ extraccion
✓ separacion
✓ transcripcion
→ traduccion
○ tts
○ mezcla
```

y reanudar exactamente donde se quedó.

### Gestión de espacio

Una película de 20 GB puede generar temporalmente ~60 GB entre audio separado,
WAV intermedios y salidas. `projects/<nombre>/` distingue explícitamente qué es
cache/temporal y qué es permanente, y el CLI expone `movie-translator clean
<nombre>` para borrar intermedios una vez que el resultado final está listo.

## 6. Modelo de datos

Segmento de transcripción (una línea de diálogo):

```json
{
  "start": 12.42,
  "end": 15.87,
  "speaker": "SPEAKER_01",
  "text": "We need to get out of here.",
  "confidence": 0.94
}
```

Mapa de hablantes (`transcription/speakers.json`; `run_diarization` lo crea
con `character: null` para cada `SPEAKER_NN` nuevo, el checkpoint humano de la
sección 3 -- `movie-translator name-speakers`, prompt interactivo -- completa
`character`; `voice` es de Fase 3/TTS y no se usa todavia):

```json
{
  "SPEAKER_01": { "character": "Neo", "voice": null },
  "SPEAKER_02": { "character": "Morpheus", "voice": null }
}
```

**Asignación de hablante a cada segmento (Fase 2):** Whisper y pyannote son
dos salidas independientes con sus propios cortes de tiempo. La regla de
asignación es la estándar: a cada segmento le corresponde el hablante del
turno de pyannote con el que más tiempo se solapa. Si un segmento no se
solapa con ningún turno (voz superpuesta, ruido, turno no detectado),
`speaker` queda en `None` -- no se inventa un hablante -- y esa línea
simplemente queda sin contexto de personaje en la traducción (ver sección 7)
hasta que se corrija a mano si hace falta.

Glosario del proyecto (nuevo respecto al boceto original — ver
`docs/DECISIONES.md` punto 4): un diccionario término→traducción que se
actualiza a medida que el proveedor de traducción decide cómo traducir un
nombre propio o una expresión recurrente, y que se le vuelve a pasar como
contexto en cada llamada siguiente para que la traducción sea consistente en
toda la película, no solo dentro de una escena.

```json
{
  "the Matrix": "la Matrix",
  "red pill": "pastilla roja"
}
```

`project.json` (estado global):

```json
{
  "project": "matrix",
  "source_language": "en",
  "target_language": "es",
  "stages": {
    "extraction": "completed",
    "separation": "completed",
    "transcription": "completed",
    "diarization": "completed",
    "translation": "running",
    "tts": "pending",
    "mixing": "pending",
    "encoding": "pending"
  }
}
```

## 7. Traducción: proveedor y consistencia

`TranslationProvider` es una interfaz única con implementaciones intercambiables
(Anthropic, OpenAI, Ollama local, y cualquier API compatible). Por decisión
tomada al arrancar el proyecto (`docs/DECISIONES.md`), el proveedor concreto no
se fija en el código: se elige por configuración (variable de entorno /
`project.json`), así que se puede cambiar de proveedor sin tocar el pipeline.

Cada llamada de traducción recibe:

- el glosario acumulado del proyecto hasta ese punto,
- el personaje que dice cada línea, cuando el proyecto ya paso por
  diarizacion (Fase 2 -- ver mas abajo),
- y, cuando aplica, la duración objetivo del hueco de tiempo (para el loop de
  sincronización de la sección 9; todavía no implementado, Fase 4).

No se traduce línea por línea de forma aislada: se agrupan en lotes de
`--batch-size` líneas consecutivas (40 por defecto), como aproximación a
"agrupar por escena" -- todavía no hay detección real de límites de escena
(ver `docs/DECISIONES.md`).

### Contexto de personaje (Fase 2)

`TranslationProvider.translate()` acepta un parámetro opcional `speakers:
dict[str, str] | None`. Las claves son el índice de la línea dentro del lote
que se está traduciendo, como string (`"0"`, `"1"`, ...), y los valores el
nombre del personaje que la dice; una línea sin hablante identificado
simplemente no aparece en el dict. `None` (o `{}`) es "sin contexto de
personaje", exactamente el comportamiento de la Fase 1 -- ningún proveedor ni
test existente se rompe por el parámetro nuevo.

`core/pipeline/translation.py` arma este dict a partir de
`transcription/speakers.json` (ver sección 6) y de `Segment.speaker`: si el
hablante de una línea todavía no fue nombrado por el checkpoint humano
(`movie-translator name-speakers`), se usa su etiqueta cruda (`SPEAKER_NN`)
como mejor esfuerzo, en vez de omitir la línea del todo. Cuando `speakers` no
es vacío, el mensaje de usuario que se le manda al proveedor cambia de un
array de strings sueltos a un array de objetos `{"speaker": ..., "text":
...}` (ver `translation/providers/prompt.py`); la respuesta esperada del
modelo no cambia: sigue siendo siempre un array plano de N strings
traducidos, en el mismo orden.

## 8. Subtítulos

El entregable de la Fase 1 no es solo "texto traducido en un .srt": tiene que
cumplir reglas de legibilidad estándar de la industria, si no, es ilegible
aunque la traducción sea perfecta:

- máximo ~17 caracteres por segundo de lectura (CPS),
- máximo 2 líneas por cue, ~42 caracteres por línea,
- duración mínima por cue (evitar subtítulos de flash de <1s).

El módulo `subtitles/` valida y reflowea el texto traducido contra estas reglas
antes de escribir el `.srt` final, y marca los cues que no cumplen para
revisión o para pedirle al traductor una versión más corta.

## 9. TTS y sincronización

Dos estrategias de proveedor (interfaz `TTSProvider`, igual patrón que
traducción): local (sin costo por minuto, requiere hardware) y cloud (mejor
calidad en algunos casos, costo por minuto). La decisión de si se clona la voz
del actor original o se usan voces genéricas queda pendiente y afecta qué
proveedor se implementa primero — ver `docs/DECISIONES.md`.

Sincronización: cuando el audio generado no cabe en el hueco de tiempo
original, no se reduce todo a "acelerar el audio":

```
duracion generada = 4.1s   espacio disponible = 3.4s   → desfase 17%

±5%   ajuste de velocidad normal (time-stretch)
±10%  ajuste aceptable, revisar si suena natural
>10%  no se estira mas: se vuelve a pedir traduccion mas corta (loop con
      seccion 7) antes de generar el audio de nuevo
```

## 10. Separación y mezcla de audio

Demucs separa el audio original en voces / música / efectos. Se descartan las
voces originales pero se conservan música y efectos, que se combinan con las
voces en español generadas por TTS:

```
musica + efectos + voces_es → mezcla final (FFmpeg)
```

## 11. Sistema de jobs

Cada etapa del pipeline es un job independiente (`pending → running →
completed` o `failed`, reintentable). Para no bloquear el proceso principal
durante horas, se implementa una cola ligera desde el principio: una tabla
SQLite con los jobs y workers en background (async), sin depender de
infraestructura externa (Redis/Airflow) hasta que de verdad haga falta escalar
a varias películas en paralelo.

## 12. Interfaz

Primero CLI (Typer), sin frontend:

```
movie-translator new matrix.mkv
movie-translator analyze matrix
movie-translator translate matrix --to es
movie-translator dub matrix --to es
movie-translator export matrix
movie-translator clean matrix
```

Una UI (progreso, edición de personajes/voces, preview) se añade en la Fase 6,
una vez que el motor funciona de punta a punta por CLI.

## 13. Hardware

Fase 1 (subtítulos) funciona razonablemente en CPU: FFmpeg, faster-whisper y
la llamada al proveedor de traducción no requieren GPU. Las fases de
diarización, TTS y separación de audio sí se benefician mucho de GPU NVIDIA
(12+ GB VRAM); se evalúa migrar cuando se llegue a esas fases, sin bloquear el
arranque del proyecto por eso. **Decisión (2026-09-14):** Fase 2 (incluida
pyannote) también se queda en CPU por ahora -- la migración real a GPU sigue
siendo Fase 7 del roadmap, no se adelanta (ver `docs/DECISIONES.md`).

## 14. Historial de este documento

- 2026-09-13: versión inicial, a partir de `proyecto.txt` y la revisión
  registrada en el proyecto.
