"""Configuración de Gunicorn para producción (ProdIES).

Workers = 2 * nCPUs + 1 (fórmula clásica). Se puede sobreescribir desde el
entorno (GUNICORN_WORKERS) sin necesidad de rebuild.

Worker class 'gthread': cada worker tiene N threads concurrentes. Ideal para
Django que es I/O-bound (DB, Redis). 4 threads × workers ≈ 4x más slots que
workers sync simples con el mismo uso de memoria.
"""
import multiprocessing
import os

# --------------------------------------------------------------------------
# Workers y threads
# --------------------------------------------------------------------------
_workers_env = int(os.environ.get('GUNICORN_WORKERS', '0'))
workers = _workers_env if _workers_env > 0 else multiprocessing.cpu_count() * 2 + 1

worker_class = 'gthread'
threads = int(os.environ.get('GUNICORN_THREADS', '4'))

# --------------------------------------------------------------------------
# Timeouts y keep-alive
# --------------------------------------------------------------------------
timeout = 60          # Worker kill si no responde en 60s.
keepalive = 5         # Segundos de keep-alive para conexiones HTTP/1.1.
graceful_timeout = 30 # Tiempo para que los workers terminen sus requests al apagar.

# --------------------------------------------------------------------------
# Reciclado de workers (previene memory leaks acumulativos)
# --------------------------------------------------------------------------
max_requests = 1000
max_requests_jitter = 100  # Aleatoriza el reciclado para evitar picos coordinados.

# --------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------
accesslog = '-'   # stdout → visible en docker compose logs
errorlog = '-'    # stderr
loglevel = 'warning'
