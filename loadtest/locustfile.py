"""Test de estrés del Prode (ProdIES) con Locust.

Simula usuarios reales que entran, se loguean, miran el fixture y el ranking,
y guardan predicciones. Sirve para medir cuántos usuarios concurrentes aguanta
el servidor antes de degradarse (latencia alta o errores).

REQUISITOS PREVIOS (en el servidor que vas a probar):
    1) Crear los usuarios de prueba que el test usa para loguearse:
         docker compose exec web python manage.py crear_usuarios_prueba --cantidad 500
    2) Tener fixture cargado (para que haya partidos que predecir):
         docker compose exec web python manage.py cargar_fixture

CÓMO CORRERLO (desde tu máquina, NO hace falta Docker):
    pip install -r loadtest/requirements.txt

    # Modo interactivo con UI web (recomendado): abrí http://localhost:8089
    locust -f loadtest/locustfile.py --host https://prodies.lyntrix.com.ar

    # Modo headless (sin UI), 200 usuarios, 20 nuevos por segundo, 5 minutos:
    locust -f loadtest/locustfile.py --host https://prodies.lyntrix.com.ar \
           --headless -u 200 -r 20 -t 5m

Variables de entorno opcionales:
    LOADTEST_USERS      cantidad de usuarios de prueba disponibles (default 500)
    LOADTEST_PASSWORD   contraseña de los usuarios de prueba (default test1234)
"""

from __future__ import annotations

import os
import random
import re

from locust import HttpUser, between, task

# Cantidad de cuentas test_XXXX creadas con crear_usuarios_prueba.
TOTAL_USUARIOS = int(os.environ.get('LOADTEST_USERS', '500'))
PASSWORD = os.environ.get('LOADTEST_PASSWORD', 'test1234')

# Extrae el token CSRF del input hidden que Django pone en cada formulario.
CSRF_RE = re.compile(r'name="csrfmiddlewaretoken" value="([^"]+)"')
# Extrae los IDs de partido disponibles en el panel para guardar predicciones.
PARTIDO_RE = re.compile(r'name="partido_id" value="(\d+)"')


def _csrf(html: str) -> str | None:
    m = CSRF_RE.search(html)
    return m.group(1) if m else None


class ProdeUser(HttpUser):
    """Un usuario simulado del Prode."""

    # Tiempo de "pensar" entre acciones (segundos), como un humano real.
    wait_time = between(1, 5)

    def on_start(self):
        """Login al inicio de la sesión de cada usuario simulado."""
        self.partido_ids = []
        self.logueado = False
        self._login()

    def _login(self):
        # GET a la página de login para obtener la cookie + token CSRF.
        resp = self.client.get('/accounts/login/', name='GET /accounts/login/')
        token = _csrf(resp.text)
        if not token:
            return

        usuario = f'test_{random.randint(1, TOTAL_USUARIOS):04d}'
        with self.client.post(
            '/accounts/login/',
            data={
                'csrfmiddlewaretoken': token,
                'username': usuario,
                'password': PASSWORD,
            },
            headers={'Referer': self.host},
            name='POST /accounts/login/',
            allow_redirects=True,
            catch_response=True,
        ) as resp:
            # Tras un login OK, Django redirige al panel (/). Si seguimos viendo
            # el form de login, las credenciales fallaron.
            if 'name="username"' in resp.text and 'password' in resp.text:
                resp.failure('Login falló (¿creaste los usuarios de prueba?)')
            else:
                self.logueado = True

    @task(5)
    def ver_panel(self):
        """Mirar el fixture (la pantalla principal). Es lo más frecuente."""
        resp = self.client.get('/', name='GET / (panel)')
        # Cacheamos los IDs de partido para usarlos al guardar predicciones.
        ids = PARTIDO_RE.findall(resp.text)
        if ids:
            self.partido_ids = ids

    @task(2)
    def ver_ranking(self):
        """Mirar la tabla de posiciones."""
        self.client.get('/ranking/', name='GET /ranking/')

    @task(3)
    def guardar_prediccion(self):
        """Cargar/actualizar una predicción para un partido al azar."""
        if not self.logueado or not self.partido_ids:
            self.ver_panel()
            if not self.partido_ids:
                return

        partido_id = random.choice(self.partido_ids)
        # El token CSRF lo tomamos del panel recién cargado.
        resp = self.client.get('/', name='GET / (panel)')
        token = _csrf(resp.text)
        if not token:
            return

        self.client.post(
            '/',
            data={
                'csrfmiddlewaretoken': token,
                'partido_id': partido_id,
                f'goles_local_{partido_id}': random.randint(0, 4),
                f'goles_visitante_{partido_id}': random.randint(0, 4),
            },
            headers={'Referer': self.host},
            name='POST / (guardar predicción)',
        )
