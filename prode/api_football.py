"""Cliente mínimo de API-Football (RapidAPI).

Centraliza las peticiones HTTP para reutilizarlas desde los management commands
`fetch_fixture` y `update_results`.
"""

import requests
from django.conf import settings


class APIFootballError(Exception):
    """Error de configuración o de respuesta de API-Football."""


def _headers():
    if not settings.API_FOOTBALL_KEY:
        raise APIFootballError(
            'Falta API_FOOTBALL_KEY. Definila en el .env o el entorno.'
        )
    return {
        'x-rapidapi-key': settings.API_FOOTBALL_KEY,
        'x-rapidapi-host': settings.API_FOOTBALL_HOST,
    }


def get_fixtures(params):
    """Devuelve la lista `response` del endpoint /v3/fixtures.

    `params` es un dict con los filtros de la API (league, season, date, etc.).
    """
    url = f'https://{settings.API_FOOTBALL_HOST}/v3/fixtures'
    try:
        resp = requests.get(
            url, headers=_headers(), params=params,
            timeout=settings.API_FOOTBALL_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise APIFootballError(f'Error consultando API-Football: {exc}') from exc

    data = resp.json()
    errores = data.get('errors')
    # La API devuelve {} cuando no hay errores, o un dict/list con
    # detalle cuando sí los hay.
    if errores:
        raise APIFootballError(f'API-Football devolvió errores: {errores}')

    return data.get('response', [])
