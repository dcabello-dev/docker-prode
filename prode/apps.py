from django.apps import AppConfig


class ProdeConfig(AppConfig):
    name = 'prode'

    def ready(self):
        # Conecta las señales (creación automática de PerfilUsuario).
        from . import signals  # noqa: F401
