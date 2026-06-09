# Imagen oficial de Python liviana (compatible con ARM y x86)
FROM python:3.12-slim

# Evita .pyc y activa logs sin buffer (ideal para ver logs en Docker)
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencias del sistema necesarias para compilar algunas libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalamos los requerimientos primero (aprovecha la caché de capas de Docker)
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el resto del código
COPY . /app/

# sed: por si el script llegó con CRLF (Windows), que rompe el shebang en Linux.
RUN sed -i 's/\r$//' /app/docker/entrypoint.sh \
    && chmod +x /app/docker/entrypoint.sh

EXPOSE 8000

# El entrypoint corre migraciones + collectstatic y luego ejecuta el CMD
ENTRYPOINT ["/app/docker/entrypoint.sh"]

# Servidor de producción: gunicorn (3 workers)
CMD ["gunicorn", "ComunidadSoft.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60"]
