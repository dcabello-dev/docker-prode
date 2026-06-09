"""Crea/actualiza el usuario administrador del Prode (no interactivo).

Lee las credenciales de variables de entorno, por lo que sirve para automatizar
el alta del admin en el servidor sin tener que responder los prompts de
`createsuperuser`. Es idempotente: si el usuario ya existe, sólo le resetea la
contraseña y se asegura de que tenga permisos de staff/superusuario.

Variables de entorno:
    DJANGO_ADMIN_USER      Nombre de usuario (default: admin)
    DJANGO_ADMIN_PASSWORD  Contraseña (obligatoria)
    DJANGO_ADMIN_EMAIL     Email (opcional)

Uso:
    python manage.py crear_admin
    python manage.py crear_admin --usuario lauti --password secreta123
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from prode.models import PerfilUsuario


class Command(BaseCommand):
    help = "Crea o actualiza el usuario administrador del Prode."

    def add_arguments(self, parser):
        parser.add_argument(
            '--usuario',
            default=os.environ.get('DJANGO_ADMIN_USER', 'admin'),
            help='Usuario del admin (default: admin o DJANGO_ADMIN_USER).',
        )
        parser.add_argument(
            '--password',
            default=os.environ.get('DJANGO_ADMIN_PASSWORD'),
            help='Contraseña del admin (o DJANGO_ADMIN_PASSWORD).',
        )
        parser.add_argument(
            '--email',
            default=os.environ.get('DJANGO_ADMIN_EMAIL', ''),
            help='Email del admin (opcional, o DJANGO_ADMIN_EMAIL).',
        )

    def handle(self, *args, **options):
        User = get_user_model()

        usuario = options['usuario']
        password = options['password']
        email = options['email']

        if not password:
            raise CommandError(
                'Falta la contraseña. Definí DJANGO_ADMIN_PASSWORD en el .env '
                'o pasala con --password.'
            )

        user, creado = User.objects.get_or_create(username=usuario)
        user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        PerfilUsuario.objects.get_or_create(usuario=user)

        if creado:
            self.stdout.write(self.style.SUCCESS(
                f"Administrador '{usuario}' creado correctamente."
            ))
        else:
            self.stdout.write(self.style.WARNING(
                f"El administrador '{usuario}' ya existía: se actualizó la "
                f"contraseña y los permisos."
            ))
