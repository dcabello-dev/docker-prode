#!/bin/sh
# ============================================================================
# Crea (o actualiza) el usuario administrador del Prode dentro del contenedor.
#
# El código vive DENTRO de la imagen Docker (no hay bind mount). Si hiciste
# git pull, este script rebuildea antes de ejecutar el comando.
#
# Uso en el servidor del IES:
#
#   1) Por variables de entorno (recomendado, lee del .env):
#        ./crear-admin.sh
#
#   2) Pasando las credenciales a mano:
#        ./crear-admin.sh lauti miPasswordSegura admin@ies.edu.ar
# ============================================================================
set -e

SERVICIO="web"

USUARIO="$1"
PASSWORD="$2"
EMAIL="$3"

echo "==> Rebuildeando imagen (para incluir el código actual)..."
docker compose build "$SERVICIO"

echo "==> Levantando el stack..."
docker compose up -d "$SERVICIO"

if [ -n "$USUARIO" ] && [ -n "$PASSWORD" ]; then
    docker compose exec \
        -e DJANGO_ADMIN_USER="$USUARIO" \
        -e DJANGO_ADMIN_PASSWORD="$PASSWORD" \
        -e DJANGO_ADMIN_EMAIL="$EMAIL" \
        "$SERVICIO" python manage.py crear_admin
else
    docker compose exec "$SERVICIO" python manage.py crear_admin
fi
