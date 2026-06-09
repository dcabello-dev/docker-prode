# Test de estrés — ProdIES

Mide cuántos usuarios concurrentes aguanta el servidor antes de degradarse
(latencia alta o errores). Usa [Locust](https://locust.io): simula usuarios que
se loguean, miran el fixture y el ranking, y guardan predicciones.

## 1. Preparar el servidor (una sola vez)

En el servidor que vas a probar (idealmente el de **testing**, no producción):

```bash
# Usuarios de prueba para que el test pueda loguearse (test_0001 .. test_0500)
docker compose exec web python manage.py crear_usuarios_prueba --cantidad 500

# Que haya partidos para predecir
docker compose exec web python manage.py cargar_fixture
```

> Probá contra **testing**, no contra producción: el test escribe predicciones
> y mete carga real. Cuando termines, podés limpiar las cuentas con:
> `docker compose exec web python manage.py crear_usuarios_prueba --limpiar`

## 2. Instalar Locust (en tu máquina, no en el server)

```bash
pip install -r loadtest/requirements.txt
```

## 3. Correr el test

### Opción A — con interfaz web (recomendado para explorar)

```bash
locust -f loadtest/locustfile.py --host https://prodies.lyntrix.com.ar
```

Abrí http://localhost:8089 y cargá:
- **Number of users**: pico de usuarios concurrentes (ej. 200).
- **Spawn rate**: cuántos usuarios nuevos por segundo (ej. 20).

Mirá en vivo el RPS, la latencia y el % de fallos. Subí los usuarios de a poco
hasta que la latencia se dispare o aparezcan errores: ese es tu techo.

### Opción B — headless (para un número fijo y reproducible)

```bash
# 200 usuarios, 20 nuevos por segundo, durante 5 minutos
locust -f loadtest/locustfile.py --host https://prodies.lyntrix.com.ar \
       --headless -u 200 -r 20 -t 5m
```

## 4. Cómo leer los resultados

- **RPS**: peticiones por segundo que el server resuelve.
- **p95 / p99 (ms)**: el 95%/99% de las respuestas tardan menos que ese valor.
  Si el p95 se va por encima de ~1–2 segundos, el servidor está sufriendo.
- **% Failures**: si empieza a subir (timeouts, 5xx), llegaste al límite.

La idea es ir subiendo usuarios hasta encontrar el punto donde la latencia o los
errores se disparan. Ese número es cuántos usuarios simultáneos aguanta hoy.

## 5. Si querés que aguante más

Sin tocar código, lo primero suele ser subir los **workers de gunicorn**
(hoy 3, en el `Dockerfile`). Una regla práctica es `2 x núcleos + 1`. También
influyen la base de datos compartida y los recursos del server. Cuando hagamos
tuning lo medimos otra vez con este mismo test para comparar.
