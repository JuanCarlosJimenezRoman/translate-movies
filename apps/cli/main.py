"""Punto de entrada del CLI. Se implementa fase a fase (ver docs/ROADMAP.md)."""

import typer

app = typer.Typer(help="Movie Translator: traduce y subtitula peliculas con IA.")


@app.command()
def version() -> None:
    """Muestra la version del proyecto (placeholder de arranque)."""
    typer.echo("movie-translator 0.1.0 (Fase 1 en construccion)")


if __name__ == "__main__":
    app()
