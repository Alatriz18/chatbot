# Usa la imagen oficial de Python 3.11
FROM python:3.11

# Establece el directorio de trabajo
WORKDIR /app

# Instala dependencias del sistema necesarias
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    unixodbc-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia los archivos de requirements primero
COPY backend/requirements.txt .

# Instala las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia el backend y el frontend
COPY backend/ .
COPY frontend/ ../frontend/

# Crea un usuario no-root para mayor seguridad
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expone el puerto que usa Flask
EXPOSE 5000

# Variables de entorno
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Comando para ejecutar con SocketIO y eventlet
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"]