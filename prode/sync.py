"""Mapeo y persistencia de eventos de SofaScore hacia el modelo Partido."""

from __future__ import annotations

from datetime import date, datetime, timezone as dt_timezone

from django.conf import settings

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


def mapear_fase_por_fecha(fecha: date) -> str | None:
    """Fallback por calendario del Mundial (configurable en settings)."""
    rangos = getattr(settings, 'SOFASCORE_FASE_FECHAS', {})
    for fase in Partido.FASE_ORDEN:
        if fase == 'GRUPOS':
            continue
        rango = rangos.get(fase)
        if not rango:
            continue
        desde = date.fromisoformat(rango[0])
        hasta = date.fromisoformat(rango[1])
        if desde <= fecha <= hasta:
            return fase

    inicio_grupos = getattr(settings, 'SOFASCORE_GRUPOS_DESDE', None)
    fin_grupos = getattr(settings, 'SOFASCORE_GRUPOS_HASTA', None)
    if inicio_grupos and fin_grupos:
        d0 = date.fromisoformat(inicio_grupos)
        d1 = date.fromisoformat(fin_grupos)
        if d0 <= fecha <= d1:
            return 'GRUPOS'
    return None


def mapear_fase(event: dict) -> str:
    """Deriva la fase desde round/tournament de SofaScore o por fecha."""
    round_info = event.get('roundInfo') or {}
    nombre = (round_info.get('name') or '').lower()
    torneo = event.get('tournament') or {}
    texto = f"{nombre} {(torneo.get('name') or '')}".lower()

    if any(x in texto for x in ('3rd', 'third', 'tercer', '3er')):
        return 'TERCERO'
    if 'semi' in texto:
        return 'SEMI'
    if 'final' in texto and 'semi' not in texto:
        return 'FINAL'
    if any(x in texto for x in ('quarter', '1/4', 'cuart')):
        return 'CUARTOS'
    if any(x in texto for x in (
        'round of 16', '1/8', 'octav', '8th', 'eighth',
    )):
        return 'OCTAVOS'
    if any(x in texto for x in (
        'round of 32', '1/16', '1/32', 'dieciseis', '16th',
        'thirty-two', '32nd', '16 avos', '16avos',
    )):
        return 'DIECISEISAVOS'
    if 'group' in texto or 'grupo' in texto:
        return 'GRUPOS'

    ts = event.get('startTimestamp')
    if ts:
        fecha = datetime.fromtimestamp(ts, tz=dt_timezone.utc).date()
        por_fecha = mapear_fase_por_fecha(fecha)
        if por_fecha:
            return por_fecha

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
