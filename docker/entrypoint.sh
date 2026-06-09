#!/bin/sh
# Entrypoint de producción: prepara la base y los estáticos antes de arrancar.
set -e

# Aplica migraciones (la base vive en el volumen montado en DJANGO_DB_PATH)
python manage.py migrate --noinput

# Recolecta los archivos estáticos (CSS del admin, etc.) para WhiteNoise
python manage.py collectstatic --noinput

# Arranca el servidor (gunicorn) pasado como CMD
exec "$@"
