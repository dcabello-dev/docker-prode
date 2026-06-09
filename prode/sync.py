"""Mapeo y persistencia de fixtures de API-Football hacia el modelo Partido."""

from django.utils.dateparse import parse_datetime

from .models import Partido

# Estados "short" de API-Football.
ESTADOS_FINALIZADOS = {'FT', 'AET', 'PEN'}
ESTADOS_EN_CURSO = {'1H', 'HT', '2H', 'ET', 'BT', 'P', 'LIVE', 'INT', 'SUSP'}


def mapear_estado(short):
    """Traduce el estado 'short' de la API al estado interno del Partido."""
    if short in ESTADOS_FINALIZADOS:
        return Partido.ESTADO_FINALIZADO
    if short in ESTADOS_EN_CURSO:
        return Partido.ESTADO_EN_CURSO
    return Partido.ESTADO_PENDIENTE


def mapear_fase(round_str):
    """Deriva la fase a partir del campo league.round de la API."""
    r = (round_str or '').lower()
    es_final = 'final' in r and 'semi' not in r
    if es_final and '3rd' not in r and 'third' not in r:
        return 'FINAL'
    if 'semi' in r:
        return 'SEMI'
    if '3rd' in r or 'third' in r:
        return 'TERCERO'
    if 'quarter' in r:
        return 'CUARTOS'
    if '16' in r or 'round of 16' in r:
        return 'OCTAVOS'
    return 'GRUPOS'


def sync_partido(fixture):
    """update_or_create de un Partido a partir de un item de /v3/fixtures.

    Devuelve (partido, creado).
    """
    fx = fixture['fixture']
    teams = fixture['teams']
    goals = fixture.get('goals', {})
    league = fixture.get('league', {})

    return Partido.objects.update_or_create(
        api_id=fx['id'],
        defaults={
            'equipo_local': teams['home']['name'],
            'equipo_visitante': teams['away']['name'],
            'logo_local': teams['home'].get('logo') or '',
            'logo_visitante': teams['away'].get('logo') or '',
            'fecha_hora': parse_datetime(fx['date']),
            'estado': mapear_estado(fx['status']['short']),
            'goles_local': goals.get('home'),
            'goles_visitante': goals.get('away'),
            'fase': mapear_fase(league.get('round')),
            'zona': (league.get('round') or '')[:40],
        },
    )
