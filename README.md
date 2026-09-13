# Movie Translator

Traduce y subtitula (y a futuro dobla) películas y videos mediante IA.

```
movie.mkv → 🎬 Movie Translator → movie.es.mkv
```

## Estado

En construcción — Fase 1 (subtítulos). Ver `docs/ROADMAP.md` para las fases y
`docs/ARCHITECTURE.md` para el diseño completo.

## Documentación

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — arquitectura, pipeline,
  modelo de datos, estructura de carpetas.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — fases, checklist de tareas y
  entregable de cada una.
- [`docs/DECISIONES.md`](docs/DECISIONES.md) — decisiones tomadas y preguntas
  abiertas.

## Desarrollo

Requiere [uv](https://docs.astral.sh/uv/).

```bash
uv sync                          # entorno base (CLI, modelos de datos)
uv sync --extra transcription    # + faster-whisper (Fase 1)
uv sync --extra subtitles        # + generación de .srt (Fase 1)
uv sync --extra translation-anthropic   # o translation-openai / translation-ollama
uv sync --extra dev              # herramientas de desarrollo (pytest, ruff, mypy)
```

Los extras están separados para no forzar la instalación de dependencias
pesadas (whisper, pyannote, demucs) antes de llegar a la fase que las
necesita.

**Nota si `uv sync` tarda muchísimo (minutos u horas) sin terminar:** probablemente
esta carpeta está montada desde otro sistema (red, WSL, unidad de Windows) y
`.venv` termina viviendo en un filesystem con latencia muy alta por archivo.
Solución: crea el entorno virtual fuera del mount y enlázalo:

```bash
mkdir -p ~/venvs/translate-movies
ln -s ~/venvs/translate-movies .venv
uv sync --extra dev
```

`.venv` ya está en `.gitignore` (como symlink o como carpeta real, cualquiera
de las dos formas funciona).

## CLI (a medida que se implemente)

```bash
movie-translator new matrix.mkv
movie-translator analyze matrix
movie-translator translate matrix --to es
movie-translator dub matrix --to es
movie-translator export matrix
movie-translator clean matrix
```
