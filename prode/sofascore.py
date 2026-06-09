"""Cliente de SofaScore (APIDOJO) vía RapidAPI."""

from __future__ import annotations

import requests
from django.conf import settings


class SofaScoreError(Exception):
    """Error de configuración o de respuesta de SofaScore/RapidAPI."""


def _headers() -> dict[str, str]:
    if not settings.RAPIDAPI_KEY:
        raise SofaScoreError(
            'Falta RAPIDAPI_KEY. Definila en el .env o el entorno.'
        )
    return {
        'X-RapidAPI-Key': settings.RAPIDAPI_KEY,
        'X-RapidAPI-Host': settings.RAPIDAPI_HOST,
    }


def list_by_date(fecha: str, inverse: bool = False) -> list[dict]:
    """Devuelve los eventos de un día (YYYY-MM-DD).

    Endpoint APIDOJO: /matches/v2/list-by-date.
    Con inverse=True pide el listado completo del día (más eventos).
    """
    url = f'https://{settings.RAPIDAPI_HOST}/matches/v2/list-by-date'
    params = {
        'Category': settings.SOFASCORE_SPORT,
        'Date': fecha,
    }
    if inverse:
        params['Inverse'] = 'true'

    try:
        resp = requests.get(
            url, headers=_headers(), params=params,
            timeout=settings.RAPIDAPI_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise SofaScoreError(f'Error consultando SofaScore: {exc}') from exc

    return extraer_eventos(resp.json())


def extraer_eventos(data) -> list[dict]:
    """Normaliza la respuesta de la API a una lista plana de eventos.

    SofaScore/APIDOJO puede devolver los eventos en distintas formas según el
    endpoint o la versión del wrapper.
    """
    if not isinstance(data, dict):
        return []

    # Forma directa: {"events": [...]}
    if isinstance(data.get('events'), list):
        return [e for e in data['events'] if _es_evento(e)]

    eventos: list[dict] = []

    # Forma anidada: sportItem.tournaments[].events
    sport_item = data.get('sportItem') or {}
    for torneo in sport_item.get('tournaments', []) or []:
        for evento in torneo.get('events', []) or []:
            if _es_evento(evento):
                eventos.append(evento)

    if eventos:
        return eventos

    # Fallback: recorrer el árbol buscando objetos con forma de partido
    vistos: set[int] = set()
    for evento in _buscar_eventos_recursivo(data):
        eid = evento.get('id')
        if eid not in vistos:
            vistos.add(eid)
            eventos.append(evento)

    return eventos


def _es_evento(obj) -> bool:
    return (
        isinstance(obj, dict)
        and 'homeTeam' in obj
        and 'awayTeam' in obj
        and 'startTimestamp' in obj
        and 'id' in obj
    )


def _buscar_eventos_recursivo(obj, limite: int = 5000) -> list[dict]:
    """Recorre el JSON y devuelve objetos que parecen eventos de partido."""
    encontrados: list[dict] = []
    _walk(obj, encontrados, limite)
    return encontrados


def _walk(obj, encontrados: list[dict], limite: int) -> None:
    if len(encontrados) >= limite:
        return
    if _es_evento(obj):
        encontrados.append(obj)
        return
    if isinstance(obj, dict):
        for valor in obj.values():
            _walk(valor, encontrados, limite)
    elif isinstance(obj, list):
        for item in obj:
            _walk(item, encontrados, limite)


def tournament_id_de_evento(event: dict) -> int | None:
    """ID del torneo único en SofaScore (uniqueTournament.id).

    En SofaScore hay dos IDs: tournament.id (fase/grupo) y
    uniqueTournament.id (el torneo principal, ej. Mundial = 16).
  """
    torneo = event.get('tournament') or {}
    unico = torneo.get('uniqueTournament') or {}
    return unico.get('id') or torneo.get('id')
