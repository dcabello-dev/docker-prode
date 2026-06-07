# Create your models here.
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

class Partido(models.Model):
    FASE_CHOICES = [
        ('GRUPOS', 'Fase de Grupos'),
        ('OCTAVOS', 'Octavos de Final'),
        ('CUARTOS', 'Cuartos de Final'),
        ('SEMI', 'Semifinal'),
        ('TERCERO', 'Tercer Puesto'),
        ('FINAL', 'Final'),
    ]
    
    equipo_local = models.CharField(max_length=50)
    codigo_local = models.CharField(max_length=2, help_text="Código ISO minúscula, ej: ar, br, fr")
    equipo_visitante = models.CharField(max_length=50)
    codigo_visitante = models.CharField(max_length=2, help_text="Código ISO minúscula")
    
    fecha_hora = models.DateTimeField()
    zona = models.CharField(max_length=20, help_text="Ej: Grupo A, Octavos 1, etc.")
    fase = models.CharField(max_length=15, choices=FASE_CHOICES, default='GRUPOS')
    
    # Se cargan a posteriori por el administrador
    goles_local_real = models.IntegerField(null=True, blank=True)
    goles_visitante_real = models.IntegerField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.equipo_local} vs {self.equipo_visitante} ({self.zona})"

    @property
    def bloqueado(self):
        # Devuelve True si faltan menos de 6 horas para el partido
        return timezone.now() >= (self.fecha_hora - timedelta(hours=6))

    # 🔑 AUTOMATIZACIÓN TRIGER: Sobrescribimos el save del partido para actualizar los puntos
    def save(self, *args, **kwargs):
        # 1. Primero guardamos los goles reales del partido en la base de datos
        super().save(*args, **kwargs)
        
        # 2. Si el administrador ya cargó el resultado real, recalculamos los prodes de los alumnos
        if self.goles_local_real is not None and self.goles_visitante_real is not None:
            # Gracias a tu related_name='predicciones', podemos buscar directo con self.predicciones.all()
            for prediccion in self.predicciones.all():
                # Invocamos TU método matemático, actualizamos el campo y guardamos la predicción
                prediccion.puntos_ganados = prediccion.calcular_puntos()
                prediccion.save()


class Prediccion(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='predicciones')
    partido = models.ForeignKey(Partido, on_delete=models.CASCADE, related_name='predicciones')
    goles_local_pred = models.IntegerField()
    goles_visitante_pred = models.IntegerField()
    puntos_ganados = models.IntegerField(default=0)

    class Meta:
        unique_together = ('usuario', 'partido')

    def calcular_puntos(self):
        # Si el partido no se jugó todavía, mantiene en 0
        if self.partido.goles_local_real is None or self.partido.goles_visitante_real is None:
            return 0
        
        gl_r, gv_r = self.partido.goles_local_real, self.partido.goles_visitante_real
        gl_p, gv_p = self.goles_local_pred, self.goles_visitante_pred

        # 1. Acierto Exacto -> 3 puntos
        if gl_r == gl_p and gv_r == gv_p:
            return 3
        
        # Determinar signos (1 = Gana Local, 2 = Gana Visitante, X = Empate)
        signo_real = '1' if gl_r > gv_r else ('2' if gl_r < gv_r else 'X')
        signo_pred = '1' if gl_p > gv_p else ('2' if gl_p < gv_p else 'X')

        if signo_real == signo_pred:
            if signo_real == 'X':
                # 2. Empate sin marcar goles exactos -> 1 punto
                return 1
            else:
                # 3. Acierta ganador pero no resultado exacto -> 2 puntos
                return 2
        
        # 4. No acierta nada -> 0 puntos
        return 0