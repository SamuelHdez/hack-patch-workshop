# Usa una imagen base oficial de Python (ligera)
FROM python:3.11-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia el archivo de requerimientos y luego instala las dependencias
# (Hacemos esto primero para aprovechar la caché de Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto del código de tu aplicación al contenedor
COPY . .

# Expone el puerto en el que corre Flask (por defecto 5000)
EXPOSE 5000

# Comando para ejecutar la aplicación
# Asegúrate de que tu archivo principal se llame 'app.py' o cambia el nombre aquí
CMD ["python", "ticketweb.py"]