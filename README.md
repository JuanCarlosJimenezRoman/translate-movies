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
uv sync                          # CLI completo de Fase 1: new, analyze, transcribe
uv sync --extra translation-anthropic   # + proveedor de traduccion (o -openai / -ollama)
uv sync --extra dev              # + herramientas de desarrollo (pytest, ruff, mypy)
```

`uv sync` a secas ya deja el CLI usable de punta a punta para la Fase 1
(extraccion + transcripcion): faster-whisper y la generacion de `.srt` son
parte del uso normal del programa, no features futuras, asi que viven en
`dependencies`, no en un extra que haya que acordarse de pedir. Los extras
que sí quedan aparte son cosas genuinamente opcionales: qué proveedor de
traduccion usar, y las dependencias pesadas de fases futuras (diarizacion,
separacion de audio, API).

**Importante:** `uv sync` (sin flags) reinstala el entorno para que quede
*exactamente* igual al conjunto de extras que le pediste en esa llamada —
si antes tenías `--extra dev` instalado y corres `uv sync` a secas, te borra
pytest/ruff/mypy (no lo que está en `dependencies`, eso siempre se queda).
Si vas a seguir trabajando en el codigo, usa `uv sync --extra dev` en vez de
`uv sync` solo.

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
