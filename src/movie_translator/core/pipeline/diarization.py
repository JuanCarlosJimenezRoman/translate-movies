"""Etapa de diarizacion: turnos de hablante (pyannote) -> Segment.speaker."""

from __future__ import annotations

from movie_translator.core.models import Project, ProjectPaths, StageName, StageStatus
from movie_translator.core.models.segment import load_segments, save_segments
from movie_translator.core.pipeline.extraction import ORIGINAL_AUDIO_FILENAME
from movie_translator.core.pipeline.transcription import TRANSCRIPT_FILENAME
from movie_translator.transcription.diarization import (
    DEFAULT_DEVICE,
    DEFAULT_MODEL,
    SpeakerInfo,
    assign_speakers,
    diarize_audio,
    load_speakers,
    save_speakers,
)


def run_diarization(
    project: Project,
    paths: ProjectPaths,
    *,
    model: str = DEFAULT_MODEL,
    hf_token: str | None = None,
    device: str = DEFAULT_DEVICE,
) -> Project:
    """Detecta hablantes en el audio y completa `speaker` en cada segmento.

    Requiere que la transcripcion ya haya terminado. Sobreescribe
    `transcription/original.json` con el campo `speaker` asignado por mayor
    solapamiento de tiempo con los turnos de pyannote (ver
    docs/DECISIONES.md; sin solapamiento, `speaker` queda en None para
    revision manual, el resto de la etapa sigue igual). Tambien crea/
    actualiza `transcription/speakers.json` con un placeholder por cada
    SPEAKER_NN nuevo (character=None), sin pisar los que ya tienen nombre
    del checkpoint humano ('movie-translator name-speakers').

    Igual que las demas etapas, cualquier fallo marca la etapa como FAILED
    y persiste el estado antes de relanzar la excepcion.
    """
    audio_path = paths.audio / ORIGINAL_AUDIO_FILENAME
    transcript_path = paths.transcription / TRANSCRIPT_FILENAME
    if not transcript_path.exists():
        raise FileNotFoundError(
            f"No existe {transcript_path}. Corre 'movie-translator transcribe' primero."
        )

    segments = load_segments(transcript_path)

    project.mark_stage(StageName.DIARIZATION, StageStatus.RUNNING)
    project.save(paths.project_json)

    try:
        turns = diarize_audio(audio_path, model=model, hf_token=hf_token, device=device)
        diarized_segments = assign_speakers(segments, turns)
        save_segments(diarized_segments, transcript_path)

        speakers = load_speakers(paths.speakers_json)
        detected_labels = {seg.speaker for seg in diarized_segments if seg.speaker is not None}
        for label in detected_labels:
            speakers.setdefault(label, SpeakerInfo())
        save_speakers(speakers, paths.speakers_json)
    except Exception:
        project.mark_stage(StageName.DIARIZATION, StageStatus.FAILED)
        project.save(paths.project_json)
        raise

    project.mark_stage(StageName.DIARIZATION, StageStatus.COMPLETED)
    project.save(paths.project_json)
    return project
