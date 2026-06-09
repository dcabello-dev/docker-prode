"""Sincroniza el fixture desde SofaScore (APIDOJO / RapidAPI).

Uso:
    python manage.py fetch_fixture
    python manage.py fetch_fixture --desde 2026-06-11 --hasta 2026-07-19
    python manage.py fetch_fixture --fecha 2026-06-14 --verbose
    python manage.py listar_torneos --fecha 2026-06-14
"""

from __future__ import annotations

from datetime import date, timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ...sofascore import SofaScoreError, list_by_date
from ...sync import pertenece_al_torneo, sync_evento


class Command(BaseCommand):
    help = 'Trae el fixture desde SofaScore y lo sincroniza en la base.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fecha', default=None,
            help='Un solo día (YYYY-MM-DD). Ignorado si usás --desde/--hasta.',
        )
        parser.add_argument(
            '--desde', default=None,
            help='Primer día del rango (YYYY-MM-DD).',
        )
        parser.add_argument(
            '--hasta', default=None,
            help='Último día del rango (YYYY-MM-DD).',
        )
        parser.add_argument(
            '--dias', type=int, default=None,
            help='Días hacia adelante desde hoy (alternativa al rango).',
        )
        parser.add_argument(
            '--tournament', type=int,
            default=settings.SOFASCORE_TOURNAMENT_ID,
            help='uniqueTournament.id de SofaScore (default del .env).',
        )
        parser.add_argument(
            '--verbose', action='store_true',
            help='Muestra diagnóstico de la API (eventos, torneos).',
        )

    def handle(self, *args, **options):
        tournament_id = options['tournament']
        if not tournament_id:
            raise CommandError(
                'Falta SOFASCORE_TOURNAMENT_ID. Definilo en el .env '
                '(es el uniqueTournament.id, ej. 16 para el Mundial) o '
                'pasá --tournament. Corré listar_torneos para descubrirlo.'
            )

        fechas = self._resolver_fechas(options)
        verbose = options['verbose']
        creados = actualizados = 0
        total_api = 0
        total_filtrados = 0

        for fecha in fechas:
            try:
                eventos = list_by_date(fecha, inverse=True)
            except SofaScoreError as exc:
                raise CommandError(str(exc))

            total_api += len(eventos)
            del_dia = 0

            if verbose:
                self.stdout.write(
                    f'  {fecha}: {len(eventos)} eventos en la API'
                )

            for event in eventos:
                if not pertenece_al_torneo(event, tournament_id):
                    continue
                total_filtrados += 1
                del_dia += 1
                _, creado = sync_evento(event)
                if creado:
                    creados += 1
                else:
                    actualizados += 1

            if verbose:
                self.stdout.write(
                    f'    → {del_dia} del torneo {tournament_id}'
                )

        if total_filtrados == 0:
            self.stdout.write(self.style.WARNING(
                f'Sin partidos del torneo {tournament_id} en {len(fechas)} '
                f'día(s). La API devolvió {total_api} eventos en total.\n'
                'Verificá SOFASCORE_TOURNAMENT_ID con: '
                'python manage.py listar_torneos --fecha <YYYY-MM-DD>'
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'Fixture sincronizado: {creados} creados, '
                f'{actualizados} actualizados '
                f'({total_filtrados} partidos en {len(fechas)} día(s)).'
            ))

    def _resolver_fechas(self, options) -> list[str]:
        if options['desde'] and options['hasta']:
            return self._rango(options['desde'], options['hasta'])
        if options['fecha']:
            return [options['fecha']]
        if options['dias']:
            hoy = timezone.localdate()
            return [
                (hoy + timedelta(days=i)).isoformat()
                for i in range(options['dias'])
            ]
        # Default: hoy + 30 días (cubre un bloque del torneo)
        hoy = timezone.localdate()
        return [(hoy + timedelta(days=i)).isoformat() for i in range(31)]

    def _rango(self, desde: str, hasta: str) -> list[str]:
        inicio = date.fromisoformat(desde)
        fin = date.fromisoformat(hasta)
        if fin < inicio:
            raise CommandError('--hasta debe ser >= --desde')
        fechas = []
        actual = inicio
        while actual <= fin:
            fechas.append(actual.isoformat())
            actual += timedelta(days=1)
        return fechas
