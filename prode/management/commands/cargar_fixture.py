from django.core.management.base import BaseCommand
from prode.models import Partido
from django.utils.dateparse import parse_datetime
from django.utils import timezone

class Command(BaseCommand):
    help = 'Carga automáticamente los 48 partidos de la Fase de Grupos con sus banderas ISO'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Iniciando la carga del fixture de Fase de Grupos..."))

        # Formato de partidos: (Local, Cod_Local, Visitante, Cod_Visitante, Zona/Grupo, Fecha_Hora_ISO)
        # Fechas simuladas para el año 2026 (Mes 06 - Junio)
        partidos_data = [
            # GRUPO A
            ("Qatar", "qa", "Ecuador", "ec", "Grupo A", "2026-06-10T13:00:00Z"),
            ("Senegal", "sn", "Países Bajos", "nl", "Grupo A", "2026-06-11T16:00:00Z"),
            ("Qatar", "qa", "Senegal", "sn", "Grupo A", "2026-06-14T13:00:00Z"),
            ("Países Bajos", "nl", "Ecuador", "ec", "Grupo A", "2026-06-14T16:00:00Z"),
            ("Países Bajos", "nl", "Qatar", "qa", "Grupo A", "2026-06-18T16:00:00Z"),
            ("Ecuador", "ec", "Senegal", "sn", "Grupo A", "2026-06-18T16:00:00Z"),

            # GRUPO B
            ("Inglaterra", "gb", "Irán", "ir", "Grupo B", "2026-06-11T13:00:00Z"),
            ("Estados Unidos", "us", "Gales", "gb-wls", "Grupo B", "2026-06-11T19:00:00Z"),
            ("Gales", "gb-wls", "Irán", "ir", "Grupo B", "2026-06-15T13:00:00Z"),
            ("Inglaterra", "gb", "Estados Unidos", "us", "Grupo B", "2026-06-15T19:00:00Z"),
            ("Gales", "gb-wls", "Inglaterra", "gb", "Grupo B", "2026-06-19T19:00:00Z"),
            ("Irán", "ir", "Estados Unidos", "us", "Grupo B", "2026-06-19T19:00:00Z"),

            # GRUPO C
            ("Argentina", "ar", "Arabia Saudita", "sa", "Grupo C", "2026-06-12T13:00:00Z"),
            ("México", "mx", "Polonia", "pl", "Grupo C", "2026-06-12T16:00:00Z"),
            ("Polonia", "pl", "Arabia Saudita", "sa", "Grupo C", "2026-06-16T13:00:00Z"),
            ("Argentina", "ar", "México", "mx", "Grupo C", "2026-06-16T19:00:00Z"),
            ("Polonia", "pl", "Argentina", "ar", "Grupo C", "2026-06-20T16:00:00Z"),
            ("Arabia Saudita", "sa", "México", "mx", "Grupo C", "2026-06-20T16:00:00Z"),

            # GRUPO D
            ("Dinamarca", "dk", "Túnez", "tn", "Grupo D", "2026-06-12T19:00:00Z"),
            ("Francia", "fr", "Australia", "au", "Grupo D", "2026-06-13T13:00:00Z"),
            ("Túnez", "tn", "Australia", "au", "Grupo D", "2026-06-17T13:00:00Z"),
            ("Francia", "fr", "Dinamarca", "dk", "Grupo D", "2026-06-17T16:00:00Z"),
            ("Túnez", "tn", "Francia", "fr", "Grupo D", "2026-06-21T16:00:00Z"),
            ("Australia", "au", "Dinamarca", "dk", "Grupo D", "2026-06-21T16:00:00Z"),

            # GRUPO E
            ("Alemania", "de", "Japón", "jp", "Grupo E", "2026-06-13T16:00:00Z"),
            ("España", "es", "Costa Rica", "cr", "Grupo E", "2026-06-13T19:00:00Z"),
            ("Japón", "jp", "Costa Rica", "cr", "Grupo E", "2026-06-17T19:00:00Z"),
            ("España", "es", "Alemania", "de", "Grupo E", "2026-06-18T13:00:00Z"),
            ("Japón", "jp", "España", "es", "Grupo E", "2026-06-22T19:00:00Z"),
            ("Costa Rica", "cr", "Alemania", "de", "Grupo E", "2026-06-22T19:00:00Z"),

            # GRUPO F
            ("Marruecos", "ma", "Croacia", "hr", "Grupo F", "2026-06-14T19:00:00Z"),
            ("Bélgica", "be", "Canadá", "ca", "Grupo F", "2026-06-15T16:00:00Z"),
            ("Bélgica", "be", "Marruecos", "ma", "Grupo F", "2026-06-19T13:00:00Z"),
            ("Croacia", "hr", "Canadá", "ca", "Grupo F", "2026-06-19T16:00:00Z"),
            ("Croacia", "hr", "Bélgica", "be", "Grupo F", "2026-06-23T16:00:00Z"),
            ("Canadá", "ca", "Marruecos", "ma", "Grupo F", "2026-06-23T16:00:00Z"),

            # GRUPO G
            ("Suiza", "ch", "Camerún", "cm", "Grupo G", "2026-06-15T13:00:00Z"),
            ("Brasil", "br", "Serbia", "rs", "Grupo G", "2026-06-16T16:00:00Z"),
            ("Camerún", "cm", "Serbia", "rs", "Grupo G", "2026-06-20T13:00:00Z"),
            ("Brasil", "br", "Suiza", "ch", "Grupo G", "2026-06-20T19:00:00Z"),
            ("Camerún", "cm", "Brasil", "br", "Grupo G", "2026-06-24T19:00:00Z"),
            ("Serbia", "rs", "Suiza", "ch", "Grupo G", "2026-06-24T19:00:00Z"),

            # GRUPO H
            ("Uruguay", "uy", "Corea del Sur", "kr", "Grupo H", "2026-06-16T13:00:00Z"),
            ("Portugal", "pt", "Ghana", "gh", "Grupo H", "2026-06-16T19:00:00Z"),
            ("Corea del Sur", "kr", "Ghana", "gh", "Grupo H", "2026-06-21T13:00:00Z"),
            ("Portugal", "pt", "Uruguay", "uy", "Grupo H", "2026-06-21T19:00:00Z"),
            ("Corea del Sur", "kr", "Portugal", "pt", "Grupo H", "2026-06-25T16:00:00Z"),
            ("Ghana", "gh", "Uruguay", "uy", "Grupo H", "2026-06-25T16:00:00Z"),
        ]

        partidos_creados = 0

        for local, cod_l, vis, cod_v, grupo, dt_str in partidos_data:
            fecha_hora_aware = parse_datetime(dt_str)
            
            # Buscamos u obtenemos el partido para evitar duplicar si corrés el comando dos veces
            partido, creado = Partido.objects.get_or_create(
                equipo_local=local,
                equipo_visitante=vis,
                zona=grupo,
                defaults={
                    'codigo_local': cod_l,
                    'codigo_visitante': cod_v,
                    'fase': 'GRUPOS',
                    'fecha_hora': fecha_hora_aware,
                    'goles_local_real': None,       # Quedan vacíos esperando al admin
                    'goles_visitante_real': None    # Quedan vacíos esperando al admin
                }
            )
            
            if creado:
                partidos_creados += 1

        self.stdout.write(self.style.SUCCESS(
            f"¡Proceso completado con éxito! Se cargaron {partidos_creados} partidos nuevos de Fase de Grupos."
        ))