"""Cliente de SofaScore: RapidAPI (APIDOJO) o API directa con curl_cffi."""

from __future__ import annotations

import requests
from django.conf import settings

DIRECT_BASE = 'https://api.sofascore.com/api/v1'

MSG_403_RAPIDAPI = (
    'RapidAPI devolvió 403 Forbidden. Verificá:\n'
    '  1. Estás suscripto al plan (aunque sea Basic gratis) en '
    'https://rapidapi.com/apidojo/api/sofascore\n'
    '  2. RAPIDAPI_KEY es la de tu cuenta RapidAPI (no otra API).\n'
    '  3. RAPIDAPI_HOST=sofascore.p.rapidapi.com\n'
    'Si no tenés suscripción, usá SOFASCORE_BACKEND=direct en el .env '
    '(consulta la API pública de SofaScore con curl_cffi).'
)


class SofaScoreError(Exception):
    """Error de configuración o de respuesta de SofaScore/RapidAPI."""


def _rapidapi_headers() -> dict[str, str]:
    if not settings.RAPIDAPI_KEY:
        raise SofaScoreError(
            'Falta RAPIDAPI_KEY. Definila en el .env o usá '
            'SOFASCORE_BACKEND=direct.'
        )
    return {
        'X-RapidAPI-Key': settings.RAPIDAPI_KEY,
        'X-RapidAPI-Host': settings.RAPIDAPI_HOST,
    }


def _browser_headers() -> dict[str, str]:
    return {
        'Accept': 'application/json',
        'Referer': 'https://www.sofascore.com/',
        'Origin': 'https://www.sofascore.com',
    }


def list_by_date(fecha: str, inverse: bool = True) -> list[dict]:
    """Devuelve los eventos de un día (YYYY-MM-DD)."""
    backend = settings.SOFASCORE_BACKEND.lower()

    if backend == 'direct':
        return _list_by_date_direct(fecha, inverse)
    if backend == 'rapidapi':
        return _list_by_date_rapidapi(fecha, inverse)

    # auto: RapidAPI si hay key, con fallback a direct ante 403
    if settings.RAPIDAPI_KEY:
        try:
            return _list_by_date_rapidapi(fecha, inverse)
        except SofaScoreError as exc:
            if '403' in str(exc):
                return _list_by_date_direct(fecha, inverse)
            raise
    return _list_by_date_direct(fecha, inverse)


def _list_by_date_rapidapi(fecha: str, inverse: bool) -> list[dict]:
    sport = settings.SOFASCORE_SPORT
    inverse_suffix = '/inverse' if inverse else ''
    variants: list[tuple[str, dict]] = [
        (
            '/matches/v2/list-by-date',
            {
                'Category': sport,
                'Date': fecha,
                **({'Inverse': 'true'} if inverse else {}),
            },
        ),
        (
            f'/sport/{sport}/scheduled-events/{fecha}{inverse_suffix}',
            {},
        ),
        (
            '/matches/list-by-date',
            {
                'category': sport,
                'date': fecha,
                **({'inverse': 'true'} if inverse else {}),
            },
        ),
    ]

    ultimo_error: Exception | None = None
    vio_403 = False

    for path, params in variants:
        url = f'https://{settings.RAPIDAPI_HOST}{path}'
        try:
            resp = requests.get(
                url,
                headers=_rapidapi_headers(),
                params=params,
                timeout=settings.RAPIDAPI_TIMEOUT,
            )
            if resp.status_code == 403:
                vio_403 = True
                ultimo_error = requests.HTTPError(
                    f'403 Forbidden: {resp.url}', response=resp,
                )
                continue
            resp.raise_for_status()
            return extraer_eventos(resp.json())
        except requests.RequestException as exc:
            ultimo_error = exc
            if getattr(exc, 'response', None) is not None:
                if exc.response.status_code == 403:
                    vio_403 = True
                    continue
            continue

    if vio_403:
        raise SofaScoreError(MSG_403_RAPIDAPI)
    raise SofaScoreError(
        f'Error consultando SofaScore vía RapidAPI: {ultimo_error}'
    ) from ultimo_error


def _list_by_date_direct(fecha: str, inverse: bool) -> list[dict]:
    try:
        from curl_cffi import requests as cffi_requests
    except ImportError as exc:
        raise SofaScoreError(
            'Falta curl_cffi para SOFASCORE_BACKEND=direct. '
            'Instalalo con: pip install curl_cffi'
        ) from exc

    sport = settings.SOFASCORE_SPORT
    path = f'/sport/{sport}/scheduled-events/{fecha}'
    if inverse:
        path += '/inverse'
    url = f'{DIRECT_BASE}{path}'

    try:
        resp = cffi_requests.get(
            url,
            impersonate='chrome',
            timeout=settings.RAPIDAPI_TIMEOUT,
            headers=_browser_headers(),
        )
    except Exception as exc:
        raise SofaScoreError(
            f'Error consultando SofaScore (direct): {exc}'
        ) from exc

    if resp.status_code == 403:
        raise SofaScoreError(
            'SofaScore bloqueó la consulta directa (403). '
            'Probá con RapidAPI suscripto o reintentá más tarde.'
        )
    if resp.status_code != 200:
        raise SofaScoreError(
            f'SofaScore respondió {resp.status_code} para {url}'
        )

    return extraer_eventos(resp.json())


def extraer_eventos(data) -> list[dict]:
    """Normaliza la respuesta de la API a una lista plana de eventos."""
    if not isinstance(data, dict):
        return []

    if isinstance(data.get('events'), list):
        return [e for e in data['events'] if _es_evento(e)]

    eventos: list[dict] = []

    sport_item = data.get('sportItem') or {}
    for torneo in sport_item.get('tournaments', []) or []:
        for evento in torneo.get('events', []) or []:
            if _es_evento(evento):
                eventos.append(evento)

    if eventos:
        return eventos

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
    """ID del torneo único en SofaScore (uniqueTournament.id)."""
    torneo = event.get('tournament') or {}
    unico = torneo.get('uniqueTournament') or {}
    return unico.get('id') or torneo.get('id')
