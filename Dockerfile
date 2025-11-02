# 1. Empezar desde una imagen base de Python
FROM python:3.11-trixie

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Copiamos el archivo de requerimientos para la instalacion de las dependencias
COPY requirements.txt .

# Ejecutamos comando para instalar las dependencias
RUN pip install --no-cache-dir -r requirements.txt

# 7. Copiar el código de la aplicación
# (Asume que 'app.py' está en el mismo directorio que este Dockerfile)
COPY app.py .

# 8. Exponer el puerto de Gradio
EXPOSE 7860

# 9. Comando para ejecutar la app
# Usamos 'python'
CMD ["python", "app.py"]