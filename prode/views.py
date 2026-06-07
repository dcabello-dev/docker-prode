from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.contrib.auth.models import User
from .models import Partido, Prediccion

@login_required
def panel_prode(request):
    partidos = Partido.objects.all().order_by('fecha_hora')
    
    if request.method == 'POST':
        partido_id = request.POST.get('partido_id')
        partido = Partido.objects.get(id=partido_id)
        
        if partido.bloqueado:
            return redirect('panel_prode')
            
        goles_local = request.POST.get(f'goles_local_{partido_id}')
        goles_visitante = request.POST.get(f'goles_visitante_{partido_id}')
        
        if goles_local is not None and goles_visitante is not None and goles_local != '' and goles_visitante != '':
            Prediccion.objects.update_or_create(
                usuario=request.user,
                partido=partido,
                defaults={
                    'goles_local_pred': int(goles_local),
                    'goles_visitante_pred': int(goles_visitante)
                }
            )
        return redirect('panel_prode')

    # Mapeamos las predicciones del usuario actual
    predicciones_usuario = {p.partido_id: p for p in Prediccion.objects.filter(usuario=request.user)}
    
    # IMPORTANTE: Construimos la lista que el HTML espera recorrer
    partidos_con_prediccion = []
    for partido in partidos:
        partidos_con_prediccion.append({
            'objeto': partido,
            'prediccion': predicciones_usuario.get(partido.id)
        })
    
    # Pasamos 'partidos_con_prediccion' en el contexto
    context = {
        'partidos_con_prediccion': partidos_con_prediccion,
    }
    return render(request, 'prode/prode.html', context)

def ranking_institucional(request):
    # Calculamos los puntos totales acumulados por cada alumno/usuario
    usuarios = User.objects.annotate(
        puntos_totales=Sum('predicciones__puntos_ganados')
    ).order_by('-puntos_totales')
    
    return render(request, 'prode/ranking.html', {'usuarios': usuarios})

def acerca_de(request):
    return render(request, 'prode/acerca_de.html')