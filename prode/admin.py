from django.contrib import admin
from .models import Partido, Prediccion

@admin.action(description='Calcular puntos de predicciones para los partidos seleccionados')
def recalcular_puntos(modeladmin, request, queryset):
    for partido in queryset:
        if partido.goles_local_real is not None and partido.goles_visitante_real is not None:
            predicciones = Prediccion.objects.filter(partido=partido)
            for pred in predicciones:
                pred.puntos_ganados = pred.calcular_puntos()
                pred.save()

@admin.register(Partido)
class PartidoAdmin(admin.ModelAdmin):
    list_display = ('equipo_local', 'equipo_visitante', 'fase', 'zona', 'fecha_hora', 'goles_local_real', 'goles_visitante_real')
    list_filter = ('fase', 'zona')
    actions = [recalcular_puntos]

admin.site.register(Prediccion)
