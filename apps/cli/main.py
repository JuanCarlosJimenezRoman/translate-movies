"""Punto de entrada del CLI. Se implementa fase a fase (ver docs/ROADMAP.md)."""

import re
from pathlib import Path

import typer
from dotenv import load_dotenv

# Carga .env de la carpeta actual (o de un ancestro) ANTES de leer cualquier
# variable de entorno (ANTHROPIC_API_KEY, HF_TOKEN, TRANSLATION_PROVIDER...):
# sin esto, python-dotenv quedaba declarado como dependencia pero nunca se
# usaba, asi que un .env con HF_TOKEN/API keys no se aplicaba solo con
# tenerlo en el archivo -- habia que exportarlo a mano en la shell. No-op si
# no existe .env (ej. en tests, o corriendo desde otra carpeta).
load_dotenv()

from movie_translator.core.models import create_project, load_project
from movie_translator.core.models.segment import load_segments
from movie_translator.core.models.stage import StageName, StageStatus
from movie_translator.core.pipeline import (
    DEFAULT_BATCH_SIZE,
    run_diarization,
    run_extraction,
    run_subtitles,
    run_transcription,
    run_translation,
)
from movie_translator.core.pipeline.transcription import TRANSCRIPT_FILENAME
from movie_translator.media.ffmpeg import (
    FFmpegError,
    FFmpegNotFoundError,
    extract_audio,
    probe,
)
from movie_translator.transcription.diarization import (
    DEFAULT_DEVICE,
    DiarizationError,
    load_speakers,
    save_speakers,
)
from movie_translator.transcription.whisper import DEFAULT_MODEL_SIZE, DEFAULT_MODELS_DIR
from movie_translator.translation.providers import TranslationError, get_provider

app = typer.Typer(help="Movie Translator: traduce y subtitula peliculas con IA.")

DEFAULT_PROJECTS_ROOT = Path("projects")

_SLUG_INVALID_RE = re.compile(r"[^a-z0-9_-]+")
_SLUG_DASHES_RE = re.compile(r"-{2,}")


def _slugify(text: str) -> str:
    """Convierte un nombre de archivo en un nombre de proyecto valido.

    Ej. 'The Matrix (1999)' -> 'the-matrix-1999'. Ver la validacion real en
    movie_translator.core.models.project._validate_name.
    """
    slug = text.strip().lower().replace(" ", "-")
    slug = _SLUG_INVALID_RE.sub("-", slug)
    slug = _SLUG_DASHES_RE.sub("-", slug).strip("-_")
    return slug or "project"


def _format_duration(seconds: float) -> str:
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours}h{minutes:02d}m{secs:02d}s"


@app.command()
def version() -> None:
    """Muestra la version del proyecto (placeholder de arranque)."""
    typer.echo("movie-translator 0.1.0 (Fase 1 en construccion)")


@app.command("probe")
def probe_cmd(video: Path) -> None:
    """Muestra la metadata de audio/video de un archivo (via ffprobe)."""
    try:
        info = probe(video)
    except (FileNotFoundError, FFmpegNotFoundError, FFmpegError) as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Duracion:        {info.duration_seconds:.1f}s")
    typer.echo(f"Tiene video:     {info.has_video}")
    typer.echo(f"Tiene audio:     {info.has_audio}")
    typer.echo(f"Sample rate:     {info.audio_sample_rate}")
    typer.echo(f"Canales:         {info.audio_channels}")


@app.command("extract-audio")
def extract_audio_cmd(
    video: Path,
    output: Path | None = typer.Option(
        None, "--output", "-o", help="Ruta del .wav de salida (por defecto: junto al video)."
    ),
    overwrite: bool = typer.Option(False, "--overwrite", help="Sobreescribir si ya existe."),
) -> None:
    """Extrae el audio de un video como WAV 16kHz mono (formato de Whisper).

    Comando suelto para pruebas manuales. El flujo normal de un proyecto usa
    `movie-translator new`, que ademas registra el resultado en project.json.
    """
    out_path = output or video.with_suffix(".wav")

    try:
        extract_audio(video, out_path, overwrite=overwrite)
    except (FileNotFoundError, FileExistsError, FFmpegNotFoundError, FFmpegError) as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    typer.secho(f"Audio extraido: {out_path}", fg=typer.colors.GREEN)


@app.command("new")
def new_cmd(
    video: Path,
    name: str | None = typer.Option(
        None, "--name", "-n", help="Nombre del proyecto (por defecto: derivado del archivo)."
    ),
    from_lang: str = typer.Option("en", "--from", help="Idioma de origen."),
    to_lang: str = typer.Option("es", "--to", help="Idioma de destino."),
    projects_root: Path = typer.Option(
        DEFAULT_PROJECTS_ROOT, "--projects-root", help="Carpeta raiz de proyectos."
    ),
) -> None:
    """Crea un proyecto nuevo a partir de un video y extrae su audio.

    El video original no se copia (ver docs/DECISIONES.md): project.json
    guarda su ruta absoluta y el pipeline lee siempre de ahi.
    """
    if not video.exists():
        typer.secho(f"Error: no existe el archivo {video}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    project_name = name or _slugify(video.stem)

    try:
        project, paths = create_project(
            projects_root, project_name, source_language=from_lang, target_language=to_lang
        )
    except (ValueError, FileExistsError) as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Proyecto '{project_name}' creado en {paths.root}")
    typer.echo("Extrayendo audio...")

    try:
        run_extraction(project, paths, video)
    except Exception as exc:
        typer.secho(f"Error extrayendo audio: {exc}", fg=typer.colors.RED)
        typer.echo(
            "El proyecto quedo creado; la etapa 'extraction' quedo en 'failed'. "
            "Corrige el problema y vuelve a correr 'new' (o reintenta cuando "
            "exista un comando 'retry')."
        )
        raise typer.Exit(code=1) from exc

    typer.secho("Audio extraido correctamente.", fg=typer.colors.GREEN)
    for line in project.progress_lines():
        typer.echo(f"  {line}")


@app.command("analyze")
def analyze_cmd(
    name: str,
    projects_root: Path = typer.Option(
        DEFAULT_PROJECTS_ROOT, "--projects-root", help="Carpeta raiz de proyectos."
    ),
) -> None:
    """Muestra el estado actual de un proyecto ya creado."""
    try:
        project, _paths = load_project(projects_root, name)
    except FileNotFoundError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Proyecto:        {project.name}")
    typer.echo(f"Idiomas:         {project.source_language} -> {project.target_language}")
    if project.duration_seconds is not None:
        typer.echo(f"Duracion:        {_format_duration(project.duration_seconds)}")
    if project.source_file:
        typer.echo(f"Fuente:          {project.source_file}")
    typer.echo("")
    for line in project.progress_lines():
        typer.echo(f"  {line}")


@app.command("transcribe")
def transcribe_cmd(
    name: str,
    model: str = typer.Option(
        DEFAULT_MODEL_SIZE, "--model", help="Tamano del modelo de faster-whisper."
    ),
    models_dir: Path = typer.Option(
        DEFAULT_MODELS_DIR, "--models-dir", help="Carpeta donde se descargan/cachean los modelos."
    ),
    projects_root: Path = typer.Option(
        DEFAULT_PROJECTS_ROOT, "--projects-root", help="Carpeta raiz de proyectos."
    ),
) -> None:
    """Transcribe el audio de un proyecto ya creado (requiere 'new' antes)."""
    try:
        project, paths = load_project(projects_root, name)
    except FileNotFoundError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    if project.stages.get(StageName.EXTRACTION) != StageStatus.COMPLETED:
        typer.secho(
            "Error: la etapa 'extraction' todavia no esta completa para este "
            "proyecto. Corre 'movie-translator new' primero.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)

    typer.echo(f"Transcribiendo con el modelo '{model}' (esto puede tardar unos minutos)...")

    try:
        run_transcription(project, paths, model_size=model, models_dir=models_dir)
    except Exception as exc:
        typer.secho(f"Error transcribiendo: {exc}", fg=typer.colors.RED)
        typer.echo("La etapa 'transcription' quedo en 'failed'. Corrige el problema y reintenta.")
        raise typer.Exit(code=1) from exc

    typer.secho("Transcripcion completada.", fg=typer.colors.GREEN)
    for line in project.progress_lines():
        typer.echo(f"  {line}")


@app.command("diarize")
def diarize_cmd(
    name: str,
    hf_token: str | None = typer.Option(
        None, "--hf-token", help="Token de Hugging Face (por defecto, env HF_TOKEN)."
    ),
    device: str = typer.Option(DEFAULT_DEVICE, "--device", help="'cpu' o 'cuda'."),
    projects_root: Path = typer.Option(
        DEFAULT_PROJECTS_ROOT, "--projects-root", help="Carpeta raiz de proyectos."
    ),
) -> None:
    """Detecta hablantes (pyannote) y asigna un SPEAKER_NN a cada segmento transcrito."""
    try:
        project, paths = load_project(projects_root, name)
    except FileNotFoundError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    if project.stages.get(StageName.TRANSCRIPTION) != StageStatus.COMPLETED:
        typer.secho(
            "Error: la etapa 'transcription' todavia no esta completa para este "
            "proyecto. Corre 'movie-translator transcribe' primero.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)

    typer.echo("Detectando hablantes (esto puede tardar unos minutos)...")

    try:
        run_diarization(project, paths, hf_token=hf_token, device=device)
    except DiarizationError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED)
        typer.echo("La etapa 'diarization' quedo en 'failed'. Corrige el problema y reintenta.")
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        typer.secho(f"Error diarizando: {exc}", fg=typer.colors.RED)
        typer.echo("La etapa 'diarization' quedo en 'failed'. Corrige el problema y reintenta.")
        raise typer.Exit(code=1) from exc

    typer.secho("Diarizacion completada.", fg=typer.colors.GREEN)
    typer.echo(f"  -> Nombra los hablantes con: movie-translator name-speakers {name}")
    for line in project.progress_lines():
        typer.echo(f"  {line}")


@app.command("name-speakers")
def name_speakers_cmd(
    name: str,
    projects_root: Path = typer.Option(
        DEFAULT_PROJECTS_ROOT, "--projects-root", help="Carpeta raiz de proyectos."
    ),
) -> None:
    """Checkpoint humano: recorre cada hablante detectado y pide su nombre de personaje.

    Muestra hasta 3 lineas de ejemplo de cada SPEAKER_NN para poder
    identificarlo. Se puede correr mas de una vez (ej. para corregir un
    nombre): los hablantes ya nombrados se muestran con su nombre actual
    como default, listo para confirmar con Enter.
    """
    try:
        project, paths = load_project(projects_root, name)
    except FileNotFoundError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    if project.stages.get(StageName.DIARIZATION) != StageStatus.COMPLETED:
        typer.secho(
            "Error: la etapa 'diarization' todavia no esta completa para este "
            "proyecto. Corre 'movie-translator diarize' primero.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)

    speakers = load_speakers(paths.speakers_json)
    if not speakers:
        typer.echo("No se detectaron hablantes en este proyecto.")
        raise typer.Exit(code=0)

    segments = load_segments(paths.transcription / TRANSCRIPT_FILENAME)

    for label in sorted(speakers):
        info = speakers[label]
        examples = [seg.text for seg in segments if seg.speaker == label][:3]

        typer.echo("")
        typer.secho(label, fg=typer.colors.CYAN, bold=True)
        for example in examples:
            typer.echo(f'    "{example}"')

        default_name = info.character or label
        character = typer.prompt("  Nombre del personaje", default=default_name)
        speakers[label] = info.model_copy(update={"character": character})

    save_speakers(speakers, paths.speakers_json)
    typer.secho(
        f"\nspeakers.json actualizado ({len(speakers)} hablante(s)).", fg=typer.colors.GREEN
    )


@app.command("translate")
def translate_cmd(
    name: str,
    provider: str | None = typer.Option(
        None,
        "--provider",
        help="anthropic/openai/ollama (por defecto: TRANSLATION_PROVIDER o anthropic).",
    ),
    model: str | None = typer.Option(
        None, "--model", help="Modelo a usar (por defecto, el que trae cada proveedor)."
    ),
    batch_size: int = typer.Option(
        DEFAULT_BATCH_SIZE, "--batch-size", help="Lineas consecutivas por llamada al proveedor."
    ),
    projects_root: Path = typer.Option(
        DEFAULT_PROJECTS_ROOT, "--projects-root", help="Carpeta raiz de proyectos."
    ),
) -> None:
    """Traduce los segmentos ya transcritos de un proyecto."""
    try:
        project, paths = load_project(projects_root, name)
    except FileNotFoundError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    if project.stages.get(StageName.TRANSCRIPTION) != StageStatus.COMPLETED:
        typer.secho(
            "Error: la etapa 'transcription' todavia no esta completa para este "
            "proyecto. Corre 'movie-translator transcribe' primero.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)

    try:
        translation_provider = get_provider(provider, model=model)
    except TranslationError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Traduciendo {project.source_language} -> {project.target_language}...")

    try:
        run_translation(project, paths, translation_provider, batch_size=batch_size)
    except Exception as exc:
        typer.secho(f"Error traduciendo: {exc}", fg=typer.colors.RED)
        typer.echo("La etapa 'translation' quedo en 'failed'. Corrige el problema y reintenta.")
        raise typer.Exit(code=1) from exc

    typer.secho("Traduccion completada.", fg=typer.colors.GREEN)
    for line in project.progress_lines():
        typer.echo(f"  {line}")


@app.command("subtitles")
def subtitles_cmd(
    name: str,
    projects_root: Path = typer.Option(
        DEFAULT_PROJECTS_ROOT, "--projects-root", help="Carpeta raiz de proyectos."
    ),
) -> None:
    """Genera el .srt final a partir de la traduccion ya completa de un proyecto."""
    try:
        project, paths = load_project(projects_root, name)
    except FileNotFoundError as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    if project.stages.get(StageName.TRANSLATION) != StageStatus.COMPLETED:
        typer.secho(
            "Error: la etapa 'translation' todavia no esta completa para este "
            "proyecto. Corre 'movie-translator translate' primero.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)

    try:
        _, warnings = run_subtitles(project, paths)
    except Exception as exc:
        typer.secho(f"Error generando subtitulos: {exc}", fg=typer.colors.RED)
        typer.echo("La etapa 'subtitles' quedo en 'failed'. Corrige el problema y reintenta.")
        raise typer.Exit(code=1) from exc

    typer.secho("Subtitulos generados.", fg=typer.colors.GREEN)
    typer.echo(f"  -> {paths.subtitles / f'{project.target_language}.srt'}")
    if warnings:
        typer.secho(
            f"  {len(warnings)} cue(s) para revisar (no cumplen reglas de legibilidad):",
            fg=typer.colors.YELLOW,
        )
        for warning in warnings:
            typer.echo(f"    - {warning}")
    for line in project.progress_lines():
        typer.echo(f"  {line}")


if __name__ == "__main__":
    app()
