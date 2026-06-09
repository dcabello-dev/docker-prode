from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import Partido, Prediccion

User = get_user_model()


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

        # Si esta fase todavía no terminó, no revelamos las próximas.
        ultima_fecha = max(it['objeto'].fecha_hora for it in items)
        if ultima_fecha >= ahora:
            break

    return visibles


@login_required
def panel_prode(request):
    partidos = Partido.objects.all().order_by('fecha_hora')

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
    # Los puntos se leen del PerfilUsuario (lo mantiene el cálculo).
    usuarios = (
        User.objects
        .select_related('perfil')
        .order_by('-perfil__puntos_totales', 'username')
    )
    return render(request, 'prode/ranking.html', {'usuarios': usuarios})
