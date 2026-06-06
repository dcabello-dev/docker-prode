# Usamos una imagen oficial de Python liviana y compatible con ARM (Raspberry Pi)
FROM python:3.12-slim

# Evita que Python escriba archivos .pyc en el disco
ENV PYTHONDONTWRITEBYTECODE=1
# Evita que Python guarde en buffer las salidas de la consola (ideal para ver logs en Docker)
ENV PYTHONUNBUFFERED=1

# Seteamos el directorio de trabajo dentro del contenedor
WORKDIR /app

# Instalamos las dependencias del sistema necesarias por si acaso
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiamos e instalamos los requerimientos primero (para aprovechar la caché de capas de Docker)
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# El comando por defecto mantendrá el servidor de desarrollo corriendo
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
