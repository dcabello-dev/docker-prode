#!/bin/sh
# ============================================================================
# Crea (o actualiza) un usuario del Prode con el tipo que elijas.
#
# El código vive DENTRO de la imagen Docker (no hay bind mount). Si hiciste
# git pull, este script rebuildea antes de ejecutar el comando.
#
# Tipos:
#   participante  Juega el Prode. Sin acceso al admin de Django. (default)
#   staff         Accede al admin de Django, pero no es superusuario.
#   admin         Superusuario: acceso total al admin de Django.
#
# Uso en el servidor del IES:
#
#   1) Interactivo (te pregunta usuario, contraseña, email y tipo):
#        ./crear-usuario.sh
#
#   2) Pasando los datos a mano (usuario password email tipo):
#        ./crear-usuario.sh lauti miClave lauti@ies.edu.ar participante
#        ./crear-usuario.sh profe miClave profe@ies.edu.ar staff
#        ./crear-usuario.sh jefe miClave jefe@ies.edu.ar admin
# ============================================================================
set -e

SERVICIO="web"

USUARIO="$1"
PASSWORD="$2"
EMAIL="$3"
TIPO="$4"

# Modo interactivo si no pasaron usuario o contraseña.
if [ -z "$USUARIO" ]; then
    printf "Usuario: "
    read -r USUARIO
fi

if [ -z "$PASSWORD" ]; then
    printf "Contraseña: "
    stty -echo 2>/dev/null || true
    read -r PASSWORD
    stty echo 2>/dev/null || true
    printf "\n"
fi

if [ -z "$EMAIL" ]; then
    printf "Email (opcional, Enter para omitir): "
    read -r EMAIL
fi

if [ -z "$TIPO" ]; then
    printf "Tipo [participante/staff/admin] (Enter = participante): "
    read -r TIPO
fi
[ -z "$TIPO" ] && TIPO="participante"

if [ -z "$USUARIO" ] || [ -z "$PASSWORD" ]; then
    echo "ERROR: usuario y contraseña son obligatorios." >&2
    exit 1
fi

echo "==> Rebuildeando imagen (para incluir el código actual)..."
docker compose build "$SERVICIO"

echo "==> Levantando el stack..."
docker compose up -d "$SERVICIO"

echo "==> Creando/actualizando usuario '$USUARIO' como '$TIPO'..."
docker compose exec "$SERVICIO" python manage.py crear_usuario \
    --usuario "$USUARIO" \
    --password "$PASSWORD" \
    --email "$EMAIL" \
    --tipo "$TIPO"
