"""Sincroniza el fixture completo del torneo desde API-Football.

Pensado para correr una vez por semana (cron). Trae todos los partidos de la
liga/temporada configuradas y hace update_or_create por api_id.

Uso:
    python manage.py fetch_fixture
    python manage.py fetch_fixture --league 1 --season 2026
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from ...api_football import APIFootballError, get_fixtures
from ...sync import sync_partido


class Command(BaseCommand):
    help = 'Trae el fixture completo desde API-Football y lo sincroniza.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--league', type=int, default=settings.API_FOOTBALL_LEAGUE_ID,
            help='ID de liga (default: API_FOOTBALL_LEAGUE_ID).',
        )
        parser.add_argument(
            '--season', type=int, default=settings.API_FOOTBALL_SEASON,
            help='Temporada (año). Default: API_FOOTBALL_SEASON.',
        )

    def handle(self, *args, **options):
        params = {'league': options['league'], 'season': options['season']}

        try:
            fixtures = get_fixtures(params)
        except APIFootballError as exc:
            raise CommandError(str(exc))

        if not fixtures:
            self.stdout.write(self.style.WARNING(
                'La API no devolvió partidos para esa liga/temporada.'
            ))
            return

        creados = actualizados = 0
        for fixture in fixtures:
            _, creado = sync_partido(fixture)
            if creado:
                creados += 1
            else:
                actualizados += 1

        self.stdout.write(self.style.SUCCESS(
            f'Fixture sincronizado: {creados} creados, '
            f'{actualizados} actualizados ({len(fixtures)} en total).'
        ))
