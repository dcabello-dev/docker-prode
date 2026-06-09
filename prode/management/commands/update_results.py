"""Actualiza resultados de partidos ya jugados y dispara el cálculo de puntos.

Estrategia de ahorro: sólo llama a la API si hay partidos vencidos y todavía
PENDIENTE, y lo hace con un único request filtrando por fecha.

Uso (cron, p. ej. cada 30 min durante el torneo):
    python manage.py update_results
    python manage.py update_results --fecha 2026-06-14
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ...api_football import APIFootballError, get_fixtures
from ...models import Partido
from ...scoring import procesar_partido
from ...sync import ESTADOS_FINALIZADOS


class Command(BaseCommand):
    help = 'Actualiza resultados de partidos jugados y calcula los puntos.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fecha', default=None,
            help='Fecha a consultar en formato YYYY-MM-DD (default: hoy).',
        )

    def handle(self, *args, **options):
        ahora = timezone.now()
        pendientes = Partido.objects.filter(
            fecha_hora__lt=ahora, estado=Partido.ESTADO_PENDIENTE,
        )

        if not pendientes.exists():
            self.stdout.write(
                'No hay partidos pendientes. Sin llamadas a la API.'
            )
            return

        fecha = options['fecha'] or timezone.localdate().isoformat()
        params = {
            'league': settings.API_FOOTBALL_LEAGUE_ID,
            'season': settings.API_FOOTBALL_SEASON,
            'date': fecha,
        }

        try:
            fixtures = get_fixtures(params)
        except APIFootballError as exc:
            raise CommandError(str(exc))

        # Indexamos la respuesta por api_id para cruzarla con los pendientes.
        por_api_id = {fx['fixture']['id']: fx for fx in fixtures}

        finalizados = 0
        predicciones = 0
        for partido in pendientes:
            fixture = por_api_id.get(partido.api_id)
            if not fixture:
                continue

            short = fixture['fixture']['status']['short']
            if short not in ESTADOS_FINALIZADOS:
                continue

            goals = fixture.get('goals', {})
            partido.goles_local = goals.get('home')
            partido.goles_visitante = goals.get('away')
            partido.estado = Partido.ESTADO_FINALIZADO
            partido.save(update_fields=[
                'goles_local', 'goles_visitante', 'estado',
            ])

            # Calcula los puntos de forma transaccional inmediatamente.
            predicciones += procesar_partido(partido)
            finalizados += 1

        self.stdout.write(self.style.SUCCESS(
            f'Partidos finalizados: {finalizados}. '
            f'Predicciones procesadas: {predicciones}.'
        ))
