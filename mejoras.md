# Mejoras y observaciones — Prode Mundial Institucional

Listado de observaciones detectadas durante el análisis del proyecto, con su
impacto y propuesta de mejora. No rompen lo principal, pero conviene tenerlas
en el radar.

---

## 1. `prode2.html` está roto / sin uso
**Estado:** Resuelto (eliminado en la refactorización de API-Football)

`prode/templates/prode/prode2.html` usa filtros y tags personalizados
(`dict_get`, `dict_item`, `attr`, `csrf_with_prediccion_built_in`) que **no
existen** en el proyecto (no hay carpeta `templatetags/`). El template que
realmente se renderiza es `prode.html`, que funciona bien.

**Propuesta:** Eliminar `prode2.html` (es un borrador viejo) para evitar
confusión.

---

## 2. El ranking no exige login
**Estado:** Pendiente

La vista `ranking_institucional` (`prode/views.py`) no tiene el decorador
`@login_required`, a diferencia de `panel_prode`. Cualquiera con el link puede
ver la tabla de posiciones.

**Propuesta:** Decidir si es intencional. Si debe ser privado, agregar
`@login_required`.

---

## 3. El cálculo de puntos es manual
**Estado:** Resuelto

El comando `update_results` ahora marca los partidos como `FINALIZADO` y dispara
automáticamente `procesar_partido` (transaccional), que calcula los puntos y los
acumula en `PerfilUsuario`. El admin conserva la acción "Recalcular puntos"
(`forzar=True`) para correcciones manuales.

---

## 4. El ranking incluye a administradores
**Estado:** Pendiente

`ranking_institucional` lista **todos** los usuarios, incluido el superusuario
/ staff, que aparecen como participantes.

**Propuesta:** Filtrar con `.filter(is_staff=False, is_superuser=False)` o un
flag de "participante".

---

## 5. Seguridad para producción
**Estado:** Resuelto parcialmente (ver Docker)

En `settings.py` originalmente estaban hardcodeados:
- `SECRET_KEY` en el código.
- `DEBUG = True`.
- `ALLOWED_HOSTS = ['*']`.

**Propuesta / hecho:** Pasar estos valores a variables de entorno (`.env`) para
el despliegue en el servidor del IES. Ya aplicado en la configuración de Docker
(`DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`,
`DJANGO_CSRF_TRUSTED_ORIGINS`).

---

## 6. Zona horaria e idioma
**Estado:** Resuelto

Originalmente `TIME_ZONE = 'UTC'` y `LANGUAGE_CODE = 'en-us'`, siendo un
proyecto argentino. La lógica de bloqueo funcionaba igual (usa `USE_TZ=True`),
pero las fechas se mostraban en inglés/UTC.

**Hecho:** Cambiado a `America/Argentina/Buenos_Aires` y `es-ar`.

---

## 7. Detalles menores de código
**Estado:** Resuelto

- `prode/urls.py`: se eliminó el import duplicado de `path`.
- `ranking.html`: se reemplazó `bg-gray-750` (inexistente) por `bg-gray-700/50`.

---

## 8. Sin tests automatizados
**Estado:** Pendiente

`prode/tests.py` está vacío. La función `Prediccion.calcular_puntos()` es la
candidata ideal para tests unitarios (acierto exacto, ganador, empate, fallo).

**Propuesta:** Escribir tests de la lógica de puntuación.

---

## 9. Sin registro de usuarios self-service
**Estado:** Informativo

Los usuarios deben ser creados manualmente por el administrador desde el panel
admin. No existe una vista de registro.

**Propuesta (opcional):** Agregar un formulario de registro si se quiere que los
compañeros se den de alta solos.

---

## 10. Base de datos: migrado a PostgreSQL
**Estado:** Resuelto

Originalmente el proyecto usaba SQLite. Se migró a **PostgreSQL 16** para el
despliegue en el servidor del IES (mejor concurrencia y robustez).

`settings.py` elige el motor según las variables de entorno: si está definido
`POSTGRES_DB` usa PostgreSQL, si no, cae a SQLite (cómodo para desarrollo local
sin Docker). El stack de `docker-compose.yml` levanta un servicio `db` con
healthcheck y volumen persistente (`prode_pgdata`), y `web` espera a que la base
esté sana antes de arrancar.
