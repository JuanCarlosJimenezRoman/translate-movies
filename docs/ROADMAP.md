# Roadmap — Movie Translator

Fases secuenciales. No se empieza una fase sin haber cerrado el entregable de
la anterior. Cada fase tiene checklist, entregable concreto y preguntas que
hay que resolver antes de darla por cerrada.

## Fase 1 — Proof of Concept: subtítulos

**Objetivo:** `movie.mkv` → `movie.es.srt` con calidad legible.

Tareas:

- [x] `media/ffmpeg`: extraer pista de audio de un `.mkv`/`.mp4`. (probe.py + extract.py, comandos CLI `probe` y `extract-audio`)
- [x] `transcription/whisper`: transcribir con faster-whisper → segmentos con
      timestamp + texto + confianza. (transcribe.py, comando CLI `transcribe`;
      modelo `small` por defecto en CPU, ver `DECISIONES.md`)
- [x] `translation/providers`: interfaz `TranslationProvider` + tres proveedores
      (Anthropic, OpenAI, Ollama), elegibles por config (`--provider` / env
      `TRANSLATION_PROVIDER`). Comando CLI `translate`.
- [x] `translation/glossary`: glosario persistente por proyecto (`translation/glossary.json`),
      se pasa como contexto en cada llamada de traducción. Nota: todavia no se
      actualiza automaticamente (ver `DECISIONES.md`, limitaciones conocidas).
- [ ] `subtitles`: generación de `.srt` con reglas de CPS/líneas/duración
      mínima (sección 8 de `ARCHITECTURE.md`).
- [x] `core/models`: `Segment`, `Project`, `project.json` con estado por etapa. (project.py + segment.py + stage.py)
- [x] `core/pipeline`: `run_extraction`, `run_transcription` y `run_translation`, cada una marca running/completed/failed y persiste en cada paso. Falta encadenar subtítulos.
- [x] `apps/cli`: `new` (crea proyecto + extrae audio), `analyze` (muestra estado), `transcribe` (faster-whisper) y `translate` (Anthropic/OpenAI/Ollama).
- [ ] `fixtures/`: un clip corto (2-5 min) para iterar sin esperar películas
      completas.
- [x] Prueba de extremo a extremo con el clip corto. Validado por Juan en su propia maquina (fuera del entorno remoto, por el bloqueo a huggingface.co): `new` + `transcribe` con un clip real con voz/canto produjeron texto transcrito correcto en `transcription/original.json`.

**Entregable:** `movie.mkv` + `movie.es.srt` generado por el CLI, corriendo en
CPU.

**Abierto antes de cerrar la fase:** falta `subtitles` (generación de `.srt`) para tener el entregable completo de la Fase 1.

## Fase 2 — Script inteligente

**Objetivo:** el script traducido tiene contexto de personaje y escena, no
solo texto suelto.

Tareas:

- [ ] `transcription/diarization`: pyannote.audio, `SPEAKER_01`, `SPEAKER_02`...
- [ ] Checkpoint humano (CLI): comando para nombrar hablantes
      (`SPEAKER_01 → Neo`) antes de traducir.
- [ ] `translation`: pasar personaje + contexto de escena en cada llamada.
- [ ] Adaptación de diálogos (no traducción literal línea por línea).

**Entregable:** `speakers.json` + traducción con nombres de personaje y
consistencia de glosario a lo largo de toda la película.

## Fase 3 — TTS

**Objetivo:** generar voces en español a partir del script traducido, sin
tocar todavía el video/audio original.

Tareas:

- [ ] Decidir: ¿clonar la voz del actor original o voces genéricas por
      personaje? (ver `DECISIONES.md`, bloquea el diseño de esta fase)
- [ ] `tts/providers`: interfaz `TTSProvider` + primera implementación.
- [ ] Selección de voz por personaje (`voices/speaker_XX.wav`).
- [ ] Generación de audio de diálogo (`dialogue_es.wav`), reproducible de
      forma independiente para evaluar calidad.

**Entregable:** `dialogue_es.wav` escuchable, separado del audio original.

## Fase 4 — Audio

**Objetivo:** integrar separación de fuentes y mezcla real.

Tareas:

- [ ] `mixing`: Demucs para separar voces / música / efectos del original.
- [ ] Loop de sincronización: ajuste de duración TTS vs. timestamp original,
      con los límites de time-stretch (±5% / ±10% / regenerar traducción)
      de la sección 9 de `ARCHITECTURE.md`.
- [ ] Mezcla final: música + efectos + voces en español.

**Entregable:** `final_mix.wav`.

## Fase 5 — Exportación

**Objetivo:** película final multiplexada.

Tareas:

- [ ] `media/ffmpeg`: multiplexar video + audio español + audio original +
      subtítulos en un único `.mkv` con pistas seleccionables.
- [ ] Metadata de pistas (idioma, etiquetas).
- [ ] `movie-translator export`.

**Entregable:** `movie_es.mkv` reproducible con selector de audio/subtítulos.

## Fase 6 — UI

**Objetivo:** dejar de depender solo del CLI.

Tareas:

- [ ] `apps/api`: FastAPI exponiendo el pipeline y el estado de jobs.
- [ ] Frontend: progreso por etapa, gestión de proyectos.
- [ ] Editor de personajes/voces (reemplaza el checkpoint humano por CLI de
      la Fase 2).
- [ ] Editor de diálogos y preview de audio antes de la mezcla final.

**Entregable:** UI usable para todo el flujo, sin tocar la terminal.

## Fase 7 — Optimización

**Objetivo:** hacerlo rápido y barato de correr repetidamente.

Tareas:

- [ ] Migración a GPU para transcripción/diarización/TTS/separación.
- [ ] Cache de resultados intermedios entre corridas.
- [ ] Paralelización (varias películas / varios jobs a la vez).
- [ ] `movie-translator clean`: borrado de intermedios (sección 5 de
      `ARCHITECTURE.md`, evita que un proyecto crezca de 20GB a 60GB+
      indefinidamente).
- [ ] Reanudación robusta ante fallos a mitad de cualquier etapa.

**Entregable:** el pipeline es viable para procesar películas de forma
recurrente, no solo como demo puntual.

## Estado actual

Estamos arrancando la **Fase 1**. Ver `DECISIONES.md` para lo que ya se
decidió y lo que sigue abierto.
