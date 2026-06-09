from django.contrib import admin

from .models import PerfilUsuario, Partido, Prediccion
from .services import calcular_puntos_prode
from .views import invalidar_cache_partidos, invalidar_cache_ranking


@admin.action(description='Recalcular puntos de los partidos seleccionados')
def recalcular_puntos(modeladmin, request, queryset):
    for partido in queryset:
        calcular_puntos_prode(partido.id, forzar=True)


@admin.register(Partido)
class PartidoAdmin(admin.ModelAdmin):
    list_display = (
        'equipo_local', 'equipo_visitante', 'fase', 'estado',
        'fecha_hora', 'goles_local', 'goles_visitante',
    )
    list_filter = ('estado', 'fase')
    search_fields = ('equipo_local', 'equipo_visitante', 'api_id')
    actions = [recalcular_puntos]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Invalida el caché de partidos y ranking cuando el admin guarda un partido.
        invalidar_cache_partidos()
        invalidar_cache_ranking()


@admin.register(Prediccion)
class PrediccionAdmin(admin.ModelAdmin):
    list_display = (
        'usuario', 'partido', 'goles_local_apostado',
        'goles_visitante_apostado', 'puntos_obtenidos', 'procesada',
    )
    list_filter = ('procesada',)
    search_fields = ('usuario__username',)


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'puntos_totales')
    ordering = ('-puntos_totales',)
