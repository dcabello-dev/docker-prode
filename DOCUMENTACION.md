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

### Reglas de puntuación (`prode/scoring.py`)

| Acierto | Puntos |
|--------|--------|
| Marcador exacto (ej. 3-1 = 3-1) | 3 |
| Acierta el resultado (ganador/empate), no el marcador | 1 |
| No acierta | 0 |

### Reglas de negocio clave

- Una predicción por usuario por partido (`unique_together`).
- Un partido queda **bloqueado** cuando faltan menos de 6 horas para su inicio
  (`Partido.bloqueado`), impidiendo cargar/editar la predicción.
- El **fixture y los resultados se sincronizan automáticamente** desde
  API-Football (comandos `fetch_fixture` y `update_results`).
- Al marcarse un partido como `FINALIZADO`, se calculan los puntos de sus
  predicciones dentro de una **transacción atómica** y se acumulan en
  `PerfilUsuario.puntos_totales`.

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
| Config DB | dj-database-url (`DATABASE_URL`) | 3.1.2 |
| Cliente HTTP | requests | 2.34.2 |
| Datos deportivos | API-Football (RapidAPI) | v3 |
| Frontend | Templates Django + Tailwind CSS (CDN) | — |
| Auth | `django.contrib.auth` (nativo) | — |
| Infra | Docker + Docker Compose | — |
| Logos/Banderas | API-Football (logo) con fallback a `flagcdn.com` | — |

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
│   ├── models.py             # Partido, Prediccion, PerfilUsuario
│   ├── views.py              # panel_prode, ranking_institucional
│   ├── admin.py              # Admin + acción "Recalcular puntos"
│   ├── api_football.py       # Cliente HTTP de API-Football (RapidAPI)
│   ├── sync.py               # Mapeo y update_or_create de fixtures
│   ├── scoring.py            # Cálculo de puntos (transaccional)
│   ├── signals.py            # Crea PerfilUsuario al alta de usuario
│   ├── urls.py
│   ├── migrations/
│   ├── management/
│   │   └── commands/
│   │       ├── crear_admin.py     # Alta no interactiva del superusuario
│   │       ├── fetch_fixture.py   # Sincroniza el fixture (semanal)
│   │       └── update_results.py  # Actualiza resultados y puntúa
│   └── templates/
│       ├── prode/            # base, prode, ranking
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
| `DATABASE_URL` | URL de conexión (la consume `dj-database-url`) | SQLite local |
| `DB_CONN_MAX_AGE` | Persistencia de conexiones (segundos) | `60` |
| `POSTGRES_DB` | Nombre de la base (contenedor `db` + arma `DATABASE_URL`) | `prode` |
| `POSTGRES_USER` | Usuario de la base | `prode` |
| `POSTGRES_PASSWORD` | Contraseña de la base (**obligatoria**) | — |
| `API_FOOTBALL_KEY` | API key de RapidAPI (**obligatoria** para sincronizar) | vacío |
| `API_FOOTBALL_HOST` | Host de la API | `api-football-v1.p.rapidapi.com` |
| `API_FOOTBALL_LEAGUE_ID` | ID de liga (1 = Mundial FIFA) | `1` |
| `API_FOOTBALL_SEASON` | Temporada (año) | `2026` |
| `DJANGO_ADMIN_USER` | Usuario admin para `crear_admin` | `admin` |
| `DJANGO_ADMIN_PASSWORD` | Contraseña admin (**obligatoria** para `crear_admin`) | — |
| `DJANGO_ADMIN_EMAIL` | Email admin | vacío |

### Selección de motor de base de datos

`settings.py` usa `dj_database_url.config()` y decide en runtime:

```
DATABASE_URL definido  →  el motor de la URL (postgres:// → PostgreSQL)
DATABASE_URL ausente   →  SQLite (desarrollo local sin Docker)
```

En Docker, `docker-compose.yml` arma el `DATABASE_URL` a partir de las
variables `POSTGRES_*` (una sola fuente de verdad para usuario/clave/base).

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

### `888c9b4` — Integrar API-Football y refactorizar el dominio
Automatización del fixture/resultados y rediseño del modelo de datos:

- **`settings.py`**: `DATABASES` ahora vía `dj-database-url` (`DATABASE_URL`,
  backend `postgresql`). Nueva config `API_FOOTBALL_*`.
- **`requirements.txt`**: `dj-database-url==3.1.2`, `requests==2.34.2`.
- **`models.py`** (reescrito):
  - `Partido`: `api_id` (único, indexado), `estado`
    (`PENDIENTE`/`EN_CURSO`/`FINALIZADO`), `goles_local`/`goles_visitante`,
    `logo_*` y se conservan `codigo_*`, `fase`, `zona` y la property `bloqueado`.
  - `Prediccion`: `goles_local_apostado`/`goles_visitante_apostado`,
    `puntos_obtenidos`, `procesada` (indexado).
  - `PerfilUsuario`: `OneToOne` con `puntos_totales` (indexado).
- **`scoring.py`** (nuevo): `calcular_puntos` (3/1/0) y `procesar_partido`
  transaccional (`transaction.atomic` + `select_for_update` + `select_related`,
  acumula en el perfil con `F()`). Idempotente; `forzar=True` para recálculo.
- **`api_football.py`** (nuevo): cliente HTTP de `/v3/fixtures` con `requests`.
- **`sync.py`** (nuevo): mapeo de estado/fase y `update_or_create` por `api_id`.
- **`signals.py`** (nuevo): crea `PerfilUsuario` al alta de usuario.
- **Comandos**: `fetch_fixture` (sincroniza el fixture, semanal) y
  `update_results` (sólo llama a la API si hay pendientes vencidos, un request
  por fecha, marca `FINALIZADO` y dispara el cálculo de puntos).
- **`admin.py`/`views.py`/templates**: adaptados a los nuevos campos; ranking
  lee de `PerfilUsuario`; logos de la API con fallback a flagcdn. Se eliminó el
  template obsoleto `prode2.html`.
- **`docker-compose.yml`**: `web` recibe `DATABASE_URL` (armado desde
  `POSTGRES_*`) y las variables `API_FOOTBALL_*`.
- **Migraciones**: `0001_initial` regenerada (sin datos que preservar).

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

# Sincronizar el fixture completo desde API-Football (semanal)
docker compose exec web python manage.py fetch_fixture

# Actualizar resultados de partidos jugados y calcular puntos (cron frecuente)
docker compose exec web python manage.py update_results

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
