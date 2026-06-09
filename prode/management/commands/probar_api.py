"""Prueba la conexión con SofaScore (RapidAPI y/o direct).

Uso:
    python manage.py probar_api
    python manage.py probar_api --fecha 2026-06-14
"""

from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from ...sofascore import (
    MSG_403_RAPIDAPI,
    SofaScoreError,
    list_by_date,
    tournament_id_de_evento,
)


class Command(BaseCommand):
    help = 'Diagnóstico de conexión con SofaScore (RapidAPI / direct).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fecha', default=None,
            help='Fecha YYYY-MM-DD (default: hoy).',
        )

    def handle(self, *args, **options):
        fecha = options['fecha'] or timezone.localdate().isoformat()
        backend = settings.SOFASCORE_BACKEND
        tournament_id = settings.SOFASCORE_TOURNAMENT_ID

        self.stdout.write(f'Backend configurado: {backend}')
        self.stdout.write(f'RAPIDAPI_KEY: {"sí" if settings.RAPIDAPI_KEY else "no"}')
        self.stdout.write(f'Torneo (SOFASCORE_TOURNAMENT_ID): {tournament_id or "(sin definir)"}')
        self.stdout.write(f'Consultando partidos del {fecha}...\n')

        try:
            eventos = list_by_date(fecha, inverse=True)
        except SofaScoreError as exc:
            self.stdout.write(self.style.ERROR(str(exc)))
            if '403' in str(exc):
                self.stdout.write('\n' + MSG_403_RAPIDAPI)
            return

        self.stdout.write(self.style.SUCCESS(
            f'OK: {len(eventos)} eventos recibidos.'
        ))

        if not tournament_id:
            self.stdout.write(self.style.WARNING(
                'Definí SOFASCORE_TOURNAMENT_ID para filtrar el Mundial.'
            ))
            return

        del_torneo = [
            e for e in eventos
            if tournament_id_de_evento(e) == tournament_id
        ]
        self.stdout.write(
            f'  → {len(del_torneo)} del torneo {tournament_id}'
        )

        if del_torneo:
            ejemplo = del_torneo[0]
            home = (ejemplo.get('homeTeam') or {}).get('name', '?')
            away = (ejemplo.get('awayTeam') or {}).get('name', '?')
            self.stdout.write(f'  Ejemplo: {home} vs {away}')
