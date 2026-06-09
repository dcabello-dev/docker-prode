"""Cliente de SofaScore (APIDOJO) vía RapidAPI.

Centraliza las peticiones HTTP para reutilizarlas desde los management commands
`fetch_fixture` y `update_results`.
"""

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


def list_by_date(fecha: str) -> list[dict]:
    """Devuelve los eventos de un día (YYYY-MM-DD).

    Endpoint: /matches/v2/list-by-date.
    """
    url = f'https://{settings.RAPIDAPI_HOST}/matches/v2/list-by-date'
    params = {'Category': settings.SOFASCORE_SPORT, 'Date': fecha}
    try:
        resp = requests.get(
            url, headers=_headers(), params=params,
            timeout=settings.RAPIDAPI_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise SofaScoreError(f'Error consultando SofaScore: {exc}') from exc

    return _extraer_eventos(resp.json())


def _extraer_eventos(data: dict) -> list[dict]:
    """Normaliza la respuesta a una lista plana de eventos.

    SofaScore devuelve los eventos en `events` o anidados por torneo dentro de
    `sportItem.tournaments[].events`. Soportamos ambas formas.
    """
    if not isinstance(data, dict):
        return []

    if isinstance(data.get('events'), list):
        return data['events']

    eventos: list[dict] = []
    sport_item = data.get('sportItem') or {}
    for torneo in sport_item.get('tournaments', []) or []:
        eventos.extend(torneo.get('events', []) or [])
    return eventos
