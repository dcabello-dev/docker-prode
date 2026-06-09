from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class Partido(models.Model):
    """Un partido del Mundial, sincronizado desde API-Football."""

    ESTADO_PENDIENTE = 'PENDIENTE'
    ESTADO_EN_CURSO = 'EN_CURSO'
    ESTADO_FINALIZADO = 'FINALIZADO'
    ESTADO_CHOICES = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_EN_CURSO, 'En curso'),
        (ESTADO_FINALIZADO, 'Finalizado'),
    ]

    FASE_CHOICES = [
        ('GRUPOS', 'Fase de Grupos'),
        ('OCTAVOS', 'Octavos de Final'),
        ('CUARTOS', 'Cuartos de Final'),
        ('SEMI', 'Semifinal'),
        ('TERCERO', 'Tercer Puesto'),
        ('FINAL', 'Final'),
    ]

    # Identificador del partido en API-Football (clave de sincronización).
    api_id = models.IntegerField(unique=True, db_index=True)

    equipo_local = models.CharField(max_length=150)
    equipo_visitante = models.CharField(max_length=150)

    # Presentación de banderas: código ISO (flagcdn) y/o logo de la API.
    codigo_local = models.CharField(max_length=2, blank=True)
    codigo_visitante = models.CharField(max_length=2, blank=True)
    logo_local = models.URLField(blank=True)
    logo_visitante = models.URLField(blank=True)

    goles_local = models.IntegerField(null=True, blank=True)
    goles_visitante = models.IntegerField(null=True, blank=True)

    # Fecha UTC convertida desde el timestamp de SofaScore.
    fecha_hora = models.DateTimeField(db_index=True)
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES,
        default=ESTADO_PENDIENTE, db_index=True,
    )

    fase = models.CharField(
        max_length=15, choices=FASE_CHOICES, default='GRUPOS',
    )
    zona = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ['fecha_hora']

    def __str__(self):
        return f"{self.equipo_local} vs {self.equipo_visitante}"

    @property
    def bloqueado(self):
        """True si faltan menos de 6 horas para el partido."""
        return timezone.now() >= (self.fecha_hora - timedelta(hours=6))


class Prediccion(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='predicciones',
    )
    partido = models.ForeignKey(
        Partido, on_delete=models.CASCADE, related_name='predicciones',
    )
    goles_local_apostado = models.IntegerField()
    goles_visitante_apostado = models.IntegerField()
    puntos_obtenidos = models.IntegerField(default=0)
    procesada = models.BooleanField(default=False, db_index=True)

    class Meta:
        unique_together = ('usuario', 'partido')

    def __str__(self):
        return f"{self.usuario} - {self.partido}"


class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='perfil',
    )
    puntos_totales = models.IntegerField(default=0, db_index=True)

    def __str__(self):
        return f"{self.usuario} ({self.puntos_totales} pts)"
