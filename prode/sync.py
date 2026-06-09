"""Mapeo y persistencia de eventos de SofaScore hacia el modelo Partido."""

from __future__ import annotations

from datetime import datetime, timezone as dt_timezone

from .models import Partido
from .sofascore import tournament_id_de_evento

CODIGO_FINALIZADO = 100
TIPOS_EN_CURSO = {'inprogress'}


def evento_finalizado(status: dict) -> bool:
    return (
        status.get('type') == 'finished'
        or status.get('code') == CODIGO_FINALIZADO
    )


def mapear_estado(status: dict) -> str:
    if evento_finalizado(status):
        return Partido.ESTADO_FINALIZADO
    if status.get('type') in TIPOS_EN_CURSO:
        return Partido.ESTADO_EN_CURSO
    return Partido.ESTADO_PENDIENTE


def mapear_fase(event: dict) -> str:
    """Deriva la fase a partir del round/tournament de SofaScore."""
    round_info = event.get('roundInfo') or {}
    nombre = (round_info.get('name') or '').lower()
    torneo = event.get('tournament') or {}
    texto = f"{nombre} {(torneo.get('name') or '')}".lower()

    if 'final' in texto and 'semi' not in texto and '3rd' not in texto:
        return 'FINAL'
    if 'semi' in texto:
        return 'SEMI'
    if '3rd' in texto or 'third' in texto:
        return 'TERCERO'
    if 'quarter' in texto or '1/4' in texto:
        return 'CUARTOS'
    if '1/8' in texto or 'round of 16' in texto or 'octav' in texto:
        return 'OCTAVOS'
    return 'GRUPOS'


def timestamp_a_datetime(ts: int) -> datetime:
    return datetime.fromtimestamp(ts, tz=dt_timezone.utc)


def sync_evento(event: dict) -> tuple[Partido, bool]:
    status = event.get('status', {}) or {}
    home_score = event.get('homeScore', {}) or {}
    away_score = event.get('awayScore', {}) or {}
    round_info = event.get('roundInfo', {}) or {}
    home = event.get('homeTeam', {}) or {}
    away = event.get('awayTeam', {}) or {}

    torneo = event.get('tournament') or {}
    zona = round_info.get('name') or torneo.get('name', '')

    return Partido.objects.update_or_create(
        api_id=event['id'],
        defaults={
            'equipo_local': home.get('name', 'Local'),
            'equipo_visitante': away.get('name', 'Visitante'),
            'codigo_local': (
                (home.get('country') or {}).get('alpha2', '').lower()
            ),
            'codigo_visitante': (
                (away.get('country') or {}).get('alpha2', '').lower()
            ),
            'logo_local': home.get('logo') or '',
            'logo_visitante': away.get('logo') or '',
            'fecha_hora': timestamp_a_datetime(event['startTimestamp']),
            'estado': mapear_estado(status),
            'goles_local': home_score.get('current'),
            'goles_visitante': away_score.get('current'),
            'fase': mapear_fase(event),
            'zona': str(zona)[:40],
        },
    )


def pertenece_al_torneo(event: dict, tournament_id: int) -> bool:
    """True si el evento corresponde al torneo configurado."""
    return tournament_id_de_evento(event) == tournament_id
