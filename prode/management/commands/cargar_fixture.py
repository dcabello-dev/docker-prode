"""Carga partidos directamente en el modelo desde un archivo JSON editable.

Sirve para cargar fixture (p. ej. las eliminatorias del Mundial 2026) sin
depender de la API. Es idempotente: hace update_or_create por api_id y NO toca
goles ni estado, así re-correrlo aplica cambios de equipos/fechas sin pisar los
resultados ya cargados.

Uso:
    python manage.py cargar_fixture
    python manage.py cargar_fixture --archivo ruta/al/fixture.json
    python manage.py cargar_fixture --solo-nuevos
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from ...models import Partido

APP_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = APP_DIR / 'data'

CAMPOS_OPCIONALES = (
    'codigo_local', 'codigo_visitante', 'logo_local', 'logo_visitante',
)


class Command(BaseCommand):
    help = 'Carga partidos en el modelo desde un JSON (sin pisar resultados).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--archivo', default=None,
            help='Ruta a un JSON. Sin esto, carga todos los de data/.',
        )
        parser.add_argument(
            '--solo-nuevos', action='store_true',
            help='Crea solo los partidos que no existan (no actualiza).',
        )

    def handle(self, *args, **options):
        if options['archivo']:
            rutas = [Path(options['archivo'])]
        else:
            rutas = sorted(DATA_DIR.glob('*.json'))

        if not rutas:
            raise CommandError(f'No hay archivos JSON en {DATA_DIR}.')

        fases_validas = {c[0] for c in Partido.FASE_CHOICES}
        solo_nuevos = options['solo_nuevos']
        total_c = total_a = total_o = 0

        for ruta in rutas:
            c, a, o = self._cargar_archivo(ruta, fases_validas, solo_nuevos)
            total_c += c
            total_a += a
            total_o += o
            self.stdout.write(
                f'  {ruta.name}: {c} creados, {a} actualizados'
                + (f', {o} omitidos' if solo_nuevos else '')
            )

        resumen = (
            f'Fixture cargado: {total_c} creados, '
            f'{total_a} actualizados'
        )
        if solo_nuevos:
            resumen += f', {total_o} omitidos (ya existían)'
        self.stdout.write(self.style.SUCCESS(resumen + '.'))

    def _cargar_archivo(self, ruta, fases_validas, solo_nuevos):
        if not ruta.exists():
            raise CommandError(f'No existe el archivo: {ruta}')

        try:
            data = json.loads(ruta.read_text(encoding='utf-8'))
        except json.JSONDecodeError as exc:
            raise CommandError(f'JSON inválido en {ruta}: {exc}')

        partidos = data.get('partidos') if isinstance(data, dict) else data
        if not isinstance(partidos, list):
            raise CommandError(
                f'{ruta.name}: debe tener una lista "partidos".'
            )

        creados = actualizados = omitidos = 0

        for i, p in enumerate(partidos, start=1):
            try:
                api_id = int(p['api_id'])
                fase = p['fase']
                fecha_hora = self._parse_fecha(p['fecha_hora'])
                local = p['equipo_local']
                visitante = p['equipo_visitante']
            except (KeyError, TypeError, ValueError) as exc:
                raise CommandError(f'Partido #{i} inválido: {exc}')

            if fase not in fases_validas:
                raise CommandError(
                    f'Partido #{i} (api_id {api_id}): fase "{fase}" inválida. '
                    f'Válidas: {sorted(fases_validas)}'
                )

            existe = Partido.objects.filter(api_id=api_id).exists()
            if existe and solo_nuevos:
                omitidos += 1
                continue

            defaults = {
                'equipo_local': str(local)[:150],
                'equipo_visitante': str(visitante)[:150],
                'fecha_hora': fecha_hora,
                'fase': fase,
                'zona': str(p.get('zona', ''))[:40],
            }
            for campo in CAMPOS_OPCIONALES:
                if p.get(campo):
                    defaults[campo] = p[campo]

            _, creado = Partido.objects.update_or_create(
                api_id=api_id, defaults=defaults,
            )
            if creado:
                creados += 1
            else:
                actualizados += 1

        return creados, actualizados, omitidos

    def _parse_fecha(self, valor: str) -> datetime:
        texto = str(valor).strip().replace('Z', '+00:00')
        dt = datetime.fromisoformat(texto)
        if dt.tzinfo is None:
            from datetime import timezone as dt_timezone
            dt = dt.replace(tzinfo=dt_timezone.utc)
        return dt
