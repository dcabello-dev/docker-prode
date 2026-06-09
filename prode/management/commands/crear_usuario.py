"""Crea o actualiza un usuario del Prode con el tipo que elijas.

Tipos disponibles:
    participante  Juega el Prode. Sin acceso al admin de Django. (default)
    staff         Accede al admin de Django, pero no es superusuario.
    admin         Superusuario: acceso total al admin de Django.

Es idempotente: si el usuario ya existe, actualiza contraseña, email y permisos
según el tipo elegido. No toca las predicciones ni los puntos.

Uso:
    python manage.py crear_usuario --usuario lauti --password secreta123
    python manage.py crear_usuario -u profe -p clave --tipo staff
    python manage.py crear_usuario -u jefe -p clave --tipo admin
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from prode.models import PerfilUsuario

TIPOS = ('participante', 'staff', 'admin')


class Command(BaseCommand):
    help = 'Crea o actualiza un usuario del Prode (participante/staff/admin).'

    def add_arguments(self, parser):
        parser.add_argument(
            '-u', '--usuario', required=True,
            help='Nombre de usuario (obligatorio).',
        )
        parser.add_argument(
            '-p', '--password', required=True,
            help='Contraseña (obligatoria).',
        )
        parser.add_argument(
            '-e', '--email', default='',
            help='Email (opcional).',
        )
        parser.add_argument(
            '-t', '--tipo', default='participante', choices=TIPOS,
            help='Tipo de usuario (default: participante).',
        )

    def handle(self, *args, **options):
        usuario = options['usuario'].strip()
        password = options['password']
        email = options['email']
        tipo = options['tipo']

        if not usuario:
            raise CommandError('El usuario no puede estar vacío.')
        if not password:
            raise CommandError('La contraseña no puede estar vacía.')

        es_staff = tipo in ('staff', 'admin')
        es_superuser = tipo == 'admin'

        User = get_user_model()
        user, creado = User.objects.get_or_create(username=usuario)
        user.email = email
        user.is_staff = es_staff
        user.is_superuser = es_superuser
        user.set_password(password)
        user.save()

        PerfilUsuario.objects.get_or_create(usuario=user)

        accion = 'creado' if creado else 'actualizado'
        self.stdout.write(self.style.SUCCESS(
            f"Usuario '{usuario}' {accion} como {tipo.upper()}."
        ))
