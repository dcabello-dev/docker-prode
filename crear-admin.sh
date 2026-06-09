#!/bin/sh
# ============================================================================
# Crea (o actualiza) el usuario administrador del Prode dentro del contenedor.
#
# Uso en el servidor del IES (con el stack ya levantado):
#
#   1) Por variables de entorno (recomendado, lee del .env):
#        ./crear-admin.sh
#
#   2) Pasando las credenciales a mano:
#        ./crear-admin.sh lauti miPasswordSegura admin@ies.edu.ar
#
# Requiere que el contenedor 'web' esté corriendo (docker compose up -d).
# ============================================================================
set -e

SERVICIO="web"

USUARIO="$1"
PASSWORD="$2"
EMAIL="$3"

if [ -n "$USUARIO" ] && [ -n "$PASSWORD" ]; then
    # Modo manual: credenciales pasadas como argumentos
    docker compose exec \
        -e DJANGO_ADMIN_USER="$USUARIO" \
        -e DJANGO_ADMIN_PASSWORD="$PASSWORD" \
        -e DJANGO_ADMIN_EMAIL="$EMAIL" \
        "$SERVICIO" python manage.py crear_admin
else
    # Modo automático: usa las variables DJANGO_ADMIN_* del .env del contenedor
    docker compose exec "$SERVICIO" python manage.py crear_admin
fi
