from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .models import Partido, Prediccion

User = get_user_model()


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

    partidos_con_prediccion = [
        {'objeto': partido, 'prediccion': predicciones_usuario.get(partido.id)}
        for partido in partidos
    ]

    return render(request, 'prode/prode.html', {
        'partidos_con_prediccion': partidos_con_prediccion,
    })


def ranking_institucional(request):
    # Los puntos se leen del PerfilUsuario (lo mantiene el cálculo).
    usuarios = (
        User.objects
        .select_related('perfil')
        .order_by('-perfil__puntos_totales', 'username')
    )
    return render(request, 'prode/ranking.html', {'usuarios': usuarios})
