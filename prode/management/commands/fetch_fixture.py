"""Sincroniza el fixture de un día desde SofaScore (APIDOJO / RapidAPI).

Hace un request a list-by-date para la fecha indicada, filtra los eventos del
torneo configurado y hace update_or_create por api_id.

Uso:
    python manage.py fetch_fixture                # fecha de hoy
    python manage.py fetch_fixture --fecha 2026-06-14 --tournament 16
"""

from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ...sofascore import SofaScoreError, list_by_date
from ...sync import sync_evento


class Command(BaseCommand):
    help = 'Trae el fixture de una fecha desde SofaScore y lo sincroniza.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fecha', default=None,
            help='Fecha a consultar en formato YYYY-MM-DD (default: hoy).',
        )
        parser.add_argument(
            '--tournament', type=int,
            default=settings.SOFASCORE_TOURNAMENT_ID,
            help='TOURNAMENT_ID de SofaScore (default del entorno).',
        )

    def handle(self, *args, **options):
        fecha = options['fecha'] or timezone.localdate().isoformat()
        tournament_id = options['tournament']

        if not tournament_id:
            raise CommandError(
                'Falta el TOURNAMENT_ID. Pasá --tournament o definí '
                'SOFASCORE_TOURNAMENT_ID en el .env.'
            )

        try:
            eventos = list_by_date(fecha)
        except SofaScoreError as exc:
            raise CommandError(str(exc))

        creados = actualizados = 0
        for event in eventos:
            torneo = event.get('tournament') or {}
            if torneo.get('id') != tournament_id:
                continue
            _, creado = sync_evento(event)
            if creado:
                creados += 1
            else:
                actualizados += 1

        self.stdout.write(self.style.SUCCESS(
            f'Fixture del {fecha}: {creados} creados, '
            f'{actualizados} actualizados.'
        ))
