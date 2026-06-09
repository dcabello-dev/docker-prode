"""Lista los torneos que devuelve SofaScore para una fecha (diagnóstico).

Sirve para descubrir el SOFASCORE_TOURNAMENT_ID correcto (uniqueTournament.id).

Uso:
    python manage.py listar_torneos --fecha 2026-06-14
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ...sofascore import SofaScoreError, list_by_date, tournament_id_de_evento


class Command(BaseCommand):
    help = 'Lista torneos de SofaScore en una fecha (para configurar el .env).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fecha', default=None,
            help='Fecha YYYY-MM-DD (default: hoy).',
        )

    def handle(self, *args, **options):
        fecha = options['fecha'] or timezone.localdate().isoformat()

        try:
            eventos = list_by_date(fecha, inverse=True)
        except SofaScoreError as exc:
            raise CommandError(str(exc))

        if not eventos:
            self.stdout.write(self.style.WARNING(
                f'La API no devolvió eventos para {fecha}. '
                'Probá otra fecha con partidos programados.'
            ))
            return

        torneos: dict[int, dict] = {}
        for event in eventos:
            tid = tournament_id_de_evento(event)
            if tid is None:
                continue
            if tid not in torneos:
                t = event.get('tournament') or {}
                u = t.get('uniqueTournament') or {}
                torneos[tid] = {
                    'nombre': u.get('name') or t.get('name', '?'),
                    'partidos': 0,
                }
            torneos[tid]['partidos'] += 1

        self.stdout.write(
            f'Torneos en {fecha} ({len(eventos)} eventos totales):\n'
        )
        ordenados = sorted(torneos.items(), key=lambda x: -x[1]['partidos'])
        for tid, info in ordenados:
            self.stdout.write(
                f'  ID {tid}: {info["nombre"]} ({info["partidos"]} partidos)'
            )
        self.stdout.write(
            '\nUsá el ID en .env como SOFASCORE_TOURNAMENT_ID=...'
        )
