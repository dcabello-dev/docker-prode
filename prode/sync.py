"""Mapeo y persistencia de eventos de SofaScore hacia el modelo Partido."""

from __future__ import annotations

from datetime import datetime, timezone as dt_timezone

from .models import Partido

# SofaScore marca el fin del partido con status.type == 'finished' o code 100.
CODIGO_FINALIZADO = 100
TIPOS_EN_CURSO = {'inprogress'}


def evento_finalizado(status: dict) -> bool:
    """True si el evento de SofaScore está finalizado."""
    return (
        status.get('type') == 'finished'
        or status.get('code') == CODIGO_FINALIZADO
    )


def mapear_estado(status: dict) -> str:
    """Traduce el status de SofaScore al estado interno del Partido."""
    if evento_finalizado(status):
        return Partido.ESTADO_FINALIZADO
    if status.get('type') in TIPOS_EN_CURSO:
        return Partido.ESTADO_EN_CURSO
    return Partido.ESTADO_PENDIENTE


def timestamp_a_datetime(ts: int) -> datetime:
    """Convierte un startTimestamp (epoch UTC) a datetime con tz UTC."""
    return datetime.fromtimestamp(ts, tz=dt_timezone.utc)


def sync_evento(event: dict) -> tuple[Partido, bool]:
    """update_or_create de un Partido a partir de un evento de SofaScore.

    Devuelve (partido, creado).
    """
    status = event.get('status', {}) or {}
    home_score = event.get('homeScore', {}) or {}
    away_score = event.get('awayScore', {}) or {}
    round_info = event.get('roundInfo', {}) or {}

    return Partido.objects.update_or_create(
        api_id=event['id'],
        defaults={
            'equipo_local': event['homeTeam']['name'],
            'equipo_visitante': event['awayTeam']['name'],
            'fecha_hora': timestamp_a_datetime(event['startTimestamp']),
            'estado': mapear_estado(status),
            'goles_local': home_score.get('current'),
            'goles_visitante': away_score.get('current'),
            'zona': (round_info.get('name') or '')[:40],
        },
    )
