from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import Partido, Prediccion

User = get_user_model()

# Claves y TTLs de caché.
# Los partidos cambian solo cuando el admin actualiza resultados o sincroniza,
# así que 2 minutos es más que suficiente y descarga la DB por completo.
_CACHE_PARTIDOS = 'partidos_todos'
_CACHE_PARTIDOS_TTL = 120  # segundos

# El ranking cambia solo cuando se recalculan puntos (poco frecuente).
_CACHE_RANKING = 'ranking_usuarios'
_CACHE_RANKING_TTL = 300  # 5 minutos


def _get_partidos():
    """Devuelve todos los partidos; usa caché para evitar queries repetidas."""
    partidos = cache.get(_CACHE_PARTIDOS)
    if partidos is None:
        partidos = list(Partido.objects.all().order_by('fecha_hora'))
        cache.set(_CACHE_PARTIDOS, partidos, _CACHE_PARTIDOS_TTL)
    return partidos


def invalidar_cache_partidos():
    """Llama a esto cuando un admin actualiza resultados o sincroniza."""
    cache.delete(_CACHE_PARTIDOS)


def invalidar_cache_ranking():
    """Llama a esto cuando se recalculan puntos."""
    cache.delete(_CACHE_RANKING)


def fases_a_mostrar(partidos_por_fase):
    """Devuelve las fases visibles: la instancia actual y las ya jugadas.

    Una fase eliminatoria recién se revela cuando la anterior terminó (todos
    sus partidos ya se jugaron). Así no se muestran cruces con equipos sin
    definir (placeholders) antes de tiempo.
    """
    ahora = timezone.now()
    nombres = dict(Partido.FASE_CHOICES)
    visibles = []

    for fase in Partido.FASE_ORDEN:
        items = partidos_por_fase.get(fase)
        if not items:
            continue

        visibles.append({
            'codigo': fase,
            'nombre': nombres[fase],
            'partidos': items,
        })

        ultima_fecha = max(it['objeto'].fecha_hora for it in items)
        if ultima_fecha >= ahora:
            break

    return visibles


@login_required
def panel_prode(request):
    if request.method == 'POST':
        partido_id = request.POST.get('partido_id')
        partido = Partido.objects.filter(id=partido_id).first()

        if partido is None or partido.bloqueado:
            return redirect('panel_prode')

        goles_local = request.POST.get(f'goles_local_{partido_id}')
        goles_visitante = request.POST.get(f'goles_visitante_{partido_id}')

        if goles_local and goles_visitante:
            Prediccion.objects.update_or_create(
                usuario=request.user,
                partido=partido,
                defaults={
                    'goles_local_apostado': int(goles_local),
                    'goles_visitante_apostado': int(goles_visitante),
                },
            )
        return redirect('panel_prode')

    # GET: carga partidos desde caché, predicciones siempre desde DB (son por usuario).
    partidos = _get_partidos()

    predicciones_usuario = {
        p.partido_id: p
        for p in Prediccion.objects.filter(usuario=request.user)
    }

    partidos_por_fase: dict[str, list] = {f: [] for f in Partido.FASE_ORDEN}
    for partido in partidos:
        partidos_por_fase.setdefault(partido.fase, []).append({
            'objeto': partido,
            'prediccion': predicciones_usuario.get(partido.id),
        })

    fases_fixture = fases_a_mostrar(partidos_por_fase)

    return render(request, 'prode/prode.html', {
        'fases_fixture': fases_fixture,
    })


def ranking_institucional(request):
    usuarios = cache.get(_CACHE_RANKING)
    if usuarios is None:
        usuarios = list(
            User.objects
            .select_related('perfil')
            .order_by('-perfil__puntos_totales', 'username')
        )
        cache.set(_CACHE_RANKING, usuarios, _CACHE_RANKING_TTL)
    return render(request, 'prode/ranking.html', {'usuarios': usuarios})


def acerca_de(request):
    return render(request, 'prode/acerca_de.html')
