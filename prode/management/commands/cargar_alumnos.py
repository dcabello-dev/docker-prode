import csv
import os
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.db import IntegrityError

class Command(BaseCommand):
    help = 'Carga masivamente usuarios alumnos desde un archivo CSV'

    def add_arguments(self, parser):
        # Permitimos pasar la ruta del archivo por consola
        parser.add_argument('csv_file', type=str, help='Ruta al archivo CSV con los alumnos')

    def handle(self, *args, **options):
        csv_path = options['csv_file']

        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f"El archivo en '{csv_path}' no existe."))
            return

        self.stdout.write(self.style.SUCCESS(f"Iniciando carga desde: {csv_path}"))
        
        usuarios_creados = 0
        usuarios_omitidos = 0

        with open(csv_path, mode='r', encoding='utf-8') as file:
            # Leemos delimitado por comas
            reader = csv.reader(file)
            
            for fila_num, fila in enumerate(reader, start=1):
                # Validamos que la fila tenga los 4 campos obligatorios
                if len(fila) < 4:
                    self.stdout.write(self.style.WARNING(
                        f"Fila {fila_num} omitida: No tiene las 4 columnas requeridas (usuario, email, pass, nombre)."
                    ))
                    usuarios_omitidos += 1
                    continue
                
                username = fila[0].strip()
                email = fila[1].strip()
                password = fila[2].strip()
                nombre_completo = fila[3].strip()

                # Separamos el nombre completo en primer nombre y apellido para Django
                partes_nombre = nombre_completo.split(' ', 1)
                first_name = partes_nombre[0]
                last_name = partes_nombre[1] if len(partes_nombre) > 1 else ''

                try:
                    # Creamos el usuario de forma segura con la contraseña cifrada
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=password,
                        first_name=first_name,
                        last_name=last_name
                    )
                    self.stdout.write(f"Usuario '{username}' creado con éxito.")
                    usuarios_creados += 1

                except IntegrityError:
                    # Si el username ya existía en la base de datos, Django salta acá
                    self.stdout.write(self.style.WARNING(
                        f"Fila {fila_num}: El usuario '{username}' ya existe en el sistema. Omitido."
                    ))
                    usuarios_omitidos += 1
                except Exception as e:
                    self.stdout.write(self.style.ERROR(
                        f"Error en fila {fila_num} ({username}): {str(e)}"
                    ))
                    usuarios_omitidos += 1

        self.stdout.write(self.style.SUCCESS(
            f"\n⚡ Proceso terminado: {usuarios_creados} creados con éxito. {usuarios_omitidos} omitidos o duplicados."
        ))