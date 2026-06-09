# Documentación técnica — Prode Mundial Institucional

Documento vivo con **todos los cambios técnicos** del proyecto. Se actualiza en
cada iteración. Pensado para que cualquier compañero de la carrera pueda
entender, mantener y desplegar el sistema.

- **Repositorio:** https://github.com/LL1121/docker-prode
- **Institución:** IES 9-018 (Malargüe)
- **Objetivo:** Prode (predicciones, no apuestas) de los partidos del Mundial,
  para unir a los compañeros y dar a conocer la carrera de Programación.

---

## 1. Descripción funcional

Aplicación web donde los usuarios (alumnos) inician sesión, cargan sus
**predicciones** de los resultados de cada partido del Mundial y compiten en un
**ranking institucional** según los puntos que acumulan.

### Reglas de puntuación (`Prediccion.calcular_puntos`)

| Acierto | Puntos |
|--------|--------|
| Resultado exacto (ej. 3-1 = 3-1) | 3 |
| Acierta el ganador, no el marcador | 2 |
| Acierta el empate, no el marcador | 1 |
| No acierta | 0 |

### Reglas de negocio clave

- Una predicción por usuario por partido (`unique_together`).
- Un partido queda **bloqueado** cuando faltan menos de 6 horas para su inicio
  (`Partido.bloqueado`), impidiendo cargar/editar la predicción.
- El resultado real y el recálculo de puntos los gestiona el administrador desde
  el panel de Django admin.

---

## 2. Stack tecnológico

| Capa | Tecnología | Versión |
|------|-----------|---------|
| Lenguaje | Python | 3.12 (imagen Docker) |
| Framework | Django | 6.0.6 |
| Servidor WSGI | gunicorn | 26.0.0 |
| Estáticos | WhiteNoise | 6.12.0 |
| Base de datos | PostgreSQL | 16 |
| Driver DB | psycopg (binary) | 3.3.4 |
| Frontend | Templates Django + Tailwind CSS (CDN) | — |
| Auth | `django.contrib.auth` (nativo) | — |
| Infra | Docker + Docker Compose | — |
| Banderas | API externa `flagcdn.com` | — |

---

## 3. Arquitectura del despliegue

```
Usuario
  │  HTTPS
  ▼
Cloudflare Tunnel  (dominio: prode.ies9018malargue.edu.ar)
  │  HTTP
  ▼
Host del servidor IES  ──►  puerto 8010
  │
  ▼
┌─────────────────────── Docker Compose (red aislada) ───────────────────────┐
│                                                                             │
│  contenedor "prode-web"            contenedor "prode-postgres"              │
│  ┌────────────────────┐            ┌────────────────────────┐              │
│  │ gunicorn :8000     │  ───SQL──► │ postgres :5432         │              │
│  │ Django + WhiteNoise│            │ volumen: prode_pgdata  │              │
│  └────────────────────┘            └────────────────────────┘              │
│   depends_on: db (service_healthy)                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

- La red es la **default** de Compose (no se comparte con otros stacks). Los
  servicios se resuelven por su `container_name` / `hostname`.
- El código vive **dentro de la imagen** (no hay bind mount), por lo que cada
  cambio requiere `docker compose build`.
- La base de datos persiste en el volumen `prode_pgdata`.

---

## 4. Estructura del proyecto

```
docker-prode/
├── ComunidadSoft/            # Proyecto Django (config)
│   ├── settings.py           # Configuración por variables de entorno
│   ├── urls.py
│   ├── wsgi.py / asgi.py
├── prode/                    # App principal
│   ├── models.py             # Partido, Prediccion
│   ├── views.py              # panel_prode, ranking_institucional
│   ├── admin.py              # Carga de partidos + acción "Calcular puntos"
│   ├── urls.py
│   ├── migrations/
│   ├── management/
│   │   └── commands/
│   │       └── crear_admin.py  # Alta no interactiva del superusuario
│   └── templates/
│       ├── prode/            # base, prode, prode2 (obsoleto), ranking
│       └── registration/     # login, logged_out
├── docker/
│   └── entrypoint.sh         # migrate + collectstatic + arranque gunicorn
├── Dockerfile                # Imagen de producción
├── docker-compose.yml        # Stack web + db
├── crear-admin.sh            # Wrapper: build + up + crear_admin
├── requirements.txt
├── .env.example              # Plantilla de variables de entorno
├── .dockerignore
├── .gitattributes            # Fuerza LF en *.sh
├── mejoras.md                # Observaciones y mejoras pendientes
└── DOCUMENTACION.md          # Este documento
```

---

## 5. Variables de entorno

Se definen en un archivo `.env` (no versionado). Plantilla en `.env.example`.

| Variable | Descripción | Default |
|----------|-------------|---------|
| `DJANGO_SECRET_KEY` | Clave secreta de Django (**obligatoria** en prod) | clave de dev |
| `DJANGO_DEBUG` | Activa modo debug | `True` (compose lo fuerza a `false`) |
| `DJANGO_ALLOWED_HOSTS` | Hosts permitidos, separados por coma (sin `https://`) | `localhost,127.0.0.1` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Orígenes CSRF, separados por coma (con `https://`) | vacío |
| `POSTGRES_DB` | Nombre de la base. **Si está, se usa PostgreSQL** | — |
| `POSTGRES_USER` | Usuario de la base | `postgres` (compose: `prode`) |
| `POSTGRES_PASSWORD` | Contraseña de la base (**obligatoria**) | — |
| `POSTGRES_HOST` | Host de la base | `db` (compose: `prode-postgres`) |
| `POSTGRES_PORT` | Puerto de la base | `5432` |
| `POSTGRES_CONN_MAX_AGE` | Persistencia de conexiones (segundos) | `60` |
| `DJANGO_ADMIN_USER` | Usuario admin para `crear_admin` | `admin` |
| `DJANGO_ADMIN_PASSWORD` | Contraseña admin (**obligatoria** para `crear_admin`) | — |
| `DJANGO_ADMIN_EMAIL` | Email admin | vacío |

### Selección de motor de base de datos

`settings.py` decide en runtime:

```
POSTGRES_DB definido  →  PostgreSQL (producción / Docker)
POSTGRES_DB ausente   →  SQLite     (desarrollo local sin Docker)
```

### Seguridad en producción (`DEBUG = False`)

- `SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')` (detrás del
  Cloudflare Tunnel que termina el HTTPS).
- `SESSION_COOKIE_SECURE = True`
- `CSRF_COOKIE_SECURE = True`

---

## 6. Registro de cambios (changelog técnico)

Cada entrada corresponde a un commit en `master`.

### `14678e6` — Primera versión del proyecto Prode
Estado inicial: proyecto Django con la app `prode`, modelos `Partido` y
`Prediccion`, vistas de panel y ranking, templates con Tailwind, y un Docker
básico para desarrollo (runserver, SQLite, código por bind mount).

### `6aa9d32` — Preparar despliegue en producción para el servidor del IES
Transformación de dev a producción:

- **`settings.py`**: lectura por variables de entorno de `SECRET_KEY`, `DEBUG`,
  `ALLOWED_HOSTS` y nuevo `CSRF_TRUSTED_ORIGINS`. Se agregó WhiteNoise al
  middleware y `STORAGES` con `CompressedManifestStaticFilesStorage`. `STATIC_ROOT`,
  `DEFAULT_AUTO_FIELD` y flags de seguridad para `DEBUG=False`. Idioma a `es-ar`
  y zona horaria a `America/Argentina/Buenos_Aires`.
- **`requirements.txt`**: `gunicorn==26.0.0` y `whitenoise==6.12.0`.
- **`Dockerfile`**: imagen de producción con `ENTRYPOINT` que ejecuta
  `docker/entrypoint.sh` y `CMD` con gunicorn (3 workers, timeout 60s).
- **`docker/entrypoint.sh`**: corre `migrate --noinput` + `collectstatic
  --noinput` y luego arranca el `CMD`.
- **`docker-compose.yml`**: servicio `web` con imagen propia, `restart:
  unless-stopped`, variables desde `.env`, volumen de datos y puerto `8010:8000`.
- **`.env.example`**, **`.dockerignore`** y **`mejoras.md`** creados.
- `.gitignore`: se agregó `staticfiles/`.

### `81f3347` — Corregir entrypoint que fallaba por finales de línea CRLF
El contenedor moría con `exec /app/docker/entrypoint.sh: no such file or
directory`. Causa: el script tenía finales de línea Windows (CRLF), por lo que
el shebang quedaba como `#!/bin/sh\r` y el intérprete no se encontraba.

- Se normalizó `entrypoint.sh` a LF.
- **`.gitattributes`** nuevo: fuerza `eol=lf` en `*.sh`.
- **`Dockerfile`**: `sed -i 's/\r$//'` sobre el entrypoint en el build, como
  red de seguridad.

### `e252d70` — Agregar comando y script para crear el usuario administrador
Alta del superusuario de forma no interactiva (automatizable):

- **`prode/management/commands/crear_admin.py`**: management command
  idempotente. Lee credenciales de `DJANGO_ADMIN_USER/PASSWORD/EMAIL` o de los
  flags `--usuario/--password/--email`. Si el usuario existe, le actualiza
  contraseña y permisos de staff/superuser; si no, lo crea. Falla con mensaje
  claro si no hay contraseña.
- **`crear-admin.sh`**: wrapper que ejecuta el comando dentro del contenedor.
- **`.env.example`**: variables `DJANGO_ADMIN_*`.

### `4bc5503` — Hacer que crear-admin.sh rebuildee la imagen antes de ejecutar
Síntoma: `Unknown command crear_admin`. Causa: el código va dentro de la imagen;
sin `build` tras un `git pull`, el contenedor seguía con la imagen vieja.

- **`crear-admin.sh`**: ahora hace `docker compose build` + `up -d` antes del
  `exec`, garantizando que el comando exista en la imagen.

### `4db28a5` — Migrar la base de datos de SQLite a PostgreSQL
Migración del motor de base de datos:

- **`requirements.txt`**: `psycopg[binary]==3.3.4`.
- **`settings.py`**: bloque `DATABASES` condicional (PostgreSQL si está
  `POSTGRES_DB`, SQLite en caso contrario).
- **`docker-compose.yml`**: nuevo servicio `db` (`postgres:16`) con healthcheck
  (`pg_isready`), volumen `prode_pgdata` y `web` con `depends_on: { db:
  service_healthy }` y variables `POSTGRES_*`.
- **`.env.example`**: variables de PostgreSQL.
- **`Dockerfile`**: se eliminó el `mkdir /app/data` (era para SQLite).
- **`mejoras.md`**: punto 10 actualizado (SQLite → PostgreSQL, resuelto).

---

## 7. Guía de despliegue (servidor del IES)

### Primera vez

```bash
git clone https://github.com/LL1121/docker-prode.git
cd docker-prode
cp .env.example .env
# Editar .env: DJANGO_SECRET_KEY, dominio, POSTGRES_PASSWORD, DJANGO_ADMIN_PASSWORD
docker compose up -d --build
docker compose exec web python manage.py crear_admin
```

### Actualizar tras nuevos cambios

```bash
git pull
docker compose up -d --build
```

### Cloudflare Tunnel

Apuntar el Public Hostname al puerto `8010` del host:

| Campo | Valor |
|-------|-------|
| Subdomain / Domain | `prode.ies9018malargue.edu.ar` |
| Service | `http://localhost:8010` |

El dominio debe figurar en `DJANGO_ALLOWED_HOSTS` y, con `https://`, en
`DJANGO_CSRF_TRUSTED_ORIGINS`.

---

## 8. Comandos útiles

```bash
# Logs en vivo del web
docker compose logs -f web

# Crear / actualizar admin (lee del .env)
docker compose exec web python manage.py crear_admin
./crear-admin.sh

# Superusuario interactivo (alternativa nativa)
docker compose exec web python manage.py createsuperuser

# Aplicar migraciones manualmente
docker compose exec web python manage.py migrate

# Abrir una shell de PostgreSQL
docker compose exec db psql -U prode -d prode

# Verificar configuración de Django
docker compose exec web python manage.py check
```

---

## 9. Pendientes

Ver `mejoras.md` para el listado detallado de observaciones y mejoras
pendientes (template obsoleto `prode2.html`, ranking sin login, automatización
del cálculo de puntos, filtrado de admins del ranking, tests, integración de
API deportiva para el fixture, etc.).
