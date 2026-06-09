"""Señales de la app prode."""

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import PerfilUsuario


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    """Crea el PerfilUsuario al dar de alta un usuario nuevo."""
    if created:
        PerfilUsuario.objects.get_or_create(usuario=instance)
