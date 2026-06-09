"""Lógica de cálculo de puntos del Prode.

Regla de negocio:
    - 3 puntos: marcador exacto.
    - 1 punto:  acierta el resultado (ganador o empate) sin el marcador exacto.
    - 0 puntos: en cualquier otro caso.
"""

from django.db import transaction
from django.db.models import F

from .models import PerfilUsuario, Prediccion


def calcular_puntos(gl_real, gv_real, gl_pred, gv_pred):
    """Función pura: puntos de una predicción contra el resultado real."""
    if gl_real == gl_pred and gv_real == gv_pred:
        return 3

    # signo: 1 gana local, -1 gana visitante, 0 empate
    signo_real = (gl_real > gv_real) - (gl_real < gv_real)
    signo_pred = (gl_pred > gv_pred) - (gl_pred < gv_pred)
    if signo_real == signo_pred:
        return 1

    return 0


@transaction.atomic
def procesar_partido(partido, forzar=False):
    """Calcula y persiste los puntos de las predicciones de un partido.

    Todo ocurre dentro de una transacción atómica con bloqueo de filas
    (`select_for_update`) para garantizar consistencia en PostgreSQL y evitar
    escrituras parciales o dobles conteos.

    - `forzar=False` (flujo normal): sólo procesa predicciones no procesadas.
    - `forzar=True` (recálculo manual): reprocesa todas, ajustando el
      perfil por el delta entre el puntaje nuevo y el anterior.

    Devuelve la cantidad de predicciones procesadas.
    """
    if partido.goles_local is None or partido.goles_visitante is None:
        return 0

    predicciones = (
        Prediccion.objects
        .select_related('usuario', 'partido')
        .filter(partido=partido)
    )
    if not forzar:
        predicciones = predicciones.filter(procesada=False)
    predicciones = predicciones.select_for_update()

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

        perfil, _ = PerfilUsuario.objects.get_or_create(usuario=pred.usuario)
        PerfilUsuario.objects.filter(pk=perfil.pk).update(
            puntos_totales=F('puntos_totales') + delta
        )
        procesadas += 1

    return procesadas
