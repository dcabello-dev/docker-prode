"""Crea usuarios de prueba en masa para los tests de carga (Locust).

Genera usuarios participante con nombres predecibles (test_0001, test_0002, ...)
y la misma contraseña, para que el test de estrés pueda loguearse con ellos.
Es idempotente: si ya existen, no los duplica.

NO usar en producción real: son cuentas de prueba. Para limpiarlas:
    python manage.py crear_usuarios_prueba --limpiar

Uso:
    python manage.py crear_usuarios_prueba --cantidad 500
    python manage.py crear_usuarios_prueba --cantidad 500 --password test1234
    python manage.py crear_usuarios_prueba --limpiar
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.db import transaction

from django.core.management.base import BaseCommand

from prode.models import PerfilUsuario

PREFIJO = 'test_'


class Command(BaseCommand):
    help = 'Crea (o limpia) usuarios de prueba para los tests de carga.'

    def add_arguments(self, parser):
        parser.add_argument(
            '-c', '--cantidad', type=int, default=500,
            help='Cantidad de usuarios de prueba a crear (default: 500).',
        )
        parser.add_argument(
            '-p', '--password', default='test1234',
            help='Contraseña común para todos (default: test1234).',
        )
        parser.add_argument(
            '--limpiar', action='store_true',
            help=f'Elimina todos los usuarios con prefijo "{PREFIJO}".',
        )

    def handle(self, *args, **options):
        User = get_user_model()

        if options['limpiar']:
            borrados, _ = User.objects.filter(
                username__startswith=PREFIJO
            ).delete()
            self.stdout.write(self.style.SUCCESS(
                f'Usuarios de prueba eliminados: {borrados}.'
            ))
            return

        cantidad = options['cantidad']
        password = options['password']
        if cantidad < 1:
            self.stdout.write(self.style.ERROR('La cantidad debe ser >= 1.'))
            return

        existentes = set(
            User.objects.filter(username__startswith=PREFIJO)
            .values_list('username', flat=True)
        )

        creados = 0
        # Hasheamos la contraseña una sola vez (todos comparten la misma) para
        # no pagar el costo del hasher por cada usuario: clave en cargas grandes.
        plantilla = User(username='_tmpl_')
        plantilla.set_password(password)
        hash_password = plantilla.password

        nuevos = []
        for i in range(1, cantidad + 1):
            username = f'{PREFIJO}{i:04d}'
            if username in existentes:
                continue
            nuevos.append(User(
                username=username,
                email=f'{username}@loadtest.local',
                password=hash_password,
                is_active=True,
            ))
            creados += 1

        with transaction.atomic():
            User.objects.bulk_create(nuevos, batch_size=500)
            # bulk_create no dispara el signal post_save, así que creamos los
            # perfiles a mano (también en masa) para no romper el ranking.
            sin_perfil = User.objects.filter(
                username__startswith=PREFIJO, perfil__isnull=True
            )
            PerfilUsuario.objects.bulk_create(
                [PerfilUsuario(usuario=u) for u in sin_perfil],
                batch_size=500,
            )

        self.stdout.write(self.style.SUCCESS(
            f'Usuarios de prueba listos: {creados} creados, '
            f'{len(existentes)} ya existían. Contraseña: "{password}".'
        ))
        if creados:
            self.stdout.write(
                f'Rango: {PREFIJO}0001 .. {PREFIJO}{cantidad:04d}'
            )
