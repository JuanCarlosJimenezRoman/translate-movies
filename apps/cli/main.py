"""Punto de entrada del CLI. Se implementa fase a fase (ver docs/ROADMAP.md)."""

from pathlib import Path

import typer

from movie_translator.media.ffmpeg import (
    FFmpegError,
    FFmpegNotFoundError,
    extract_audio,
    probe,
)

app = typer.Typer(help="Movie Translator: traduce y subtitula peliculas con IA.")


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
    """Extrae el audio de un video como WAV 16kHz mono (formato de Whisper)."""
    out_path = output or video.with_suffix(".wav")

    try:
        extract_audio(video, out_path, overwrite=overwrite)
    except (FileNotFoundError, FileExistsError, FFmpegNotFoundError, FFmpegError) as exc:
        typer.secho(f"Error: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    typer.secho(f"Audio extraido: {out_path}", fg=typer.colors.GREEN)


if __name__ == "__main__":
    app()
