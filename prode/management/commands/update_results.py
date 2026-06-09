"""Actualiza resultados de partidos jugados y dispara el cálculo de puntos.

Estrategia de ahorro de cuota: sólo llama a la API si hay partidos vencidos y
todavía PENDIENTE, y hace un único request por cada día involucrado.

Uso (cron, p. ej. cada 30 min durante el torneo):
    python manage.py update_results
"""

from __future__ import annotations

from datetime import timezone as dt_timezone

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ...models import Partido
from ...services import calcular_puntos_prode
from ...sofascore import SofaScoreError, list_by_date
from ...sync import evento_finalizado


class Command(BaseCommand):
    help = 'Actualiza resultados de partidos jugados y calcula los puntos.'

    def handle(self, *args, **options):
        ahora = timezone.now()
        pendientes = list(
            Partido.objects.filter(
                fecha_hora__lt=ahora, estado=Partido.ESTADO_PENDIENTE,
            )
        )

        if not pendientes:
            self.stdout.write(
                'No hay partidos pendientes. Sin llamadas a la API.'
            )
            return

        # Indexamos por api_id y agrupamos las fechas (UTC) a consultar.
        pend_por_api = {p.api_id: p for p in pendientes}
        fechas = sorted({
            p.fecha_hora.astimezone(dt_timezone.utc).date().isoformat()
            for p in pendientes
        })

        finalizados = 0
        predicciones = 0
        for fecha in fechas:
            try:
                eventos = list_by_date(fecha)
            except SofaScoreError as exc:
                raise CommandError(str(exc))

            for event in eventos:
                partido = pend_por_api.get(event.get('id'))
                if partido is None:
                    continue
                if not evento_finalizado(event.get('status', {}) or {}):
                    continue

                home_score = event.get('homeScore', {}) or {}
                away_score = event.get('awayScore', {}) or {}
                partido.goles_local = home_score.get('current')
                partido.goles_visitante = away_score.get('current')
                partido.estado = Partido.ESTADO_FINALIZADO
                partido.save(update_fields=[
                    'goles_local', 'goles_visitante', 'estado',
                ])

                predicciones += calcular_puntos_prode(partido.id)
                finalizados += 1

        self.stdout.write(self.style.SUCCESS(
            f'Partidos finalizados: {finalizados}. '
            f'Predicciones procesadas: {predicciones}.'
        ))
