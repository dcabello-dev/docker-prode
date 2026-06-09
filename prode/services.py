"""Lógica de negocio del Prode: cálculo de puntos.

Regla de puntuación:
    - 3 puntos: marcador exacto (goles de ambos equipos).
    - 1 punto:  acierta el resultado (ganador o empate) sin el marcador exacto.
    - 0 puntos: en cualquier otro caso.
"""

from __future__ import annotations

from django.db import transaction
from django.db.models import F

from .models import PerfilUsuario, Partido, Prediccion


def calcular_puntos(gl_real: int, gv_real: int,
                    gl_pred: int, gv_pred: int) -> int:
    """Función pura: puntos de una predicción contra el resultado real."""
    if gl_real == gl_pred and gv_real == gv_pred:
        return 3

    # signo: 1 gana local, -1 gana visitante, 0 empate
    signo_real = (gl_real > gv_real) - (gl_real < gv_real)
    signo_pred = (gl_pred > gv_pred) - (gl_pred < gv_pred)
    return 1 if signo_real == signo_pred else 0


@transaction.atomic
def calcular_puntos_prode(partido_id: int, forzar: bool = False) -> int:
    """Procesa las predicciones de un partido finalizado.

    Encapsula todo en una transacción atómica e impacta el perfil del usuario
    con `F()` (incremento a nivel de fila). Usa
    `select_related('usuario__perfil')` para evitar el problema N+1.

    - `forzar=False` (flujo normal): sólo procesa predicciones no procesadas.
    - `forzar=True` (recálculo manual): reprocesa todas ajustando por el delta.

    Devuelve la cantidad de predicciones procesadas.
    """
    partido = Partido.objects.get(pk=partido_id)
    if partido.goles_local is None or partido.goles_visitante is None:
        return 0

    predicciones = (
        Prediccion.objects
        .select_related('usuario__perfil')
        .filter(partido=partido)
    )
    if not forzar:
        predicciones = predicciones.filter(procesada=False)
    # of=('self',): bloquea sólo las filas de Prediccion (compatible con el
    # outer join nullable del perfil en PostgreSQL).
    predicciones = predicciones.select_for_update(of=('self',))

    procesadas = 0
    for pred in predicciones:
        nuevos_puntos = calcular_puntos(
            partido.goles_local, partido.goles_visitante,
            pred.goles_local_apostado, pred.goles_visitante_apostado,
        )
        anteriores = pred.puntos_obtenidos if pred.procesada else 0
        delta = nuevos_puntos - anteriores

        pred.puntos_obtenidos = nuevos_puntos
        pred.procesada = True
        pred.save(update_fields=['puntos_obtenidos', 'procesada'])

        # El perfil viene precargado por select_related (sin query extra).
        perfil = getattr(pred.usuario, 'perfil', None)
        if perfil is None:
            perfil = PerfilUsuario.objects.create(usuario=pred.usuario)
        PerfilUsuario.objects.filter(pk=perfil.pk).update(
            puntos_totales=F('puntos_totales') + delta
        )
        procesadas += 1

    # Invalida el caché del ranking y partidos (los puntos cambiaron).
    from .views import invalidar_cache_ranking, invalidar_cache_partidos
    invalidar_cache_ranking()
    invalidar_cache_partidos()

    return procesadas
