# Taller: App de Traducción (GenAI + MLflow + Docker)

Este documento describe la arquitectura de la aplicación de traducción, el manejo de claves de API y los comandos utilizados para su despliegue. Sigue el despliegue y publicación. Siga los pasos del 1 al 6 si quiere hacer build y ejecución de la aplicación desde cero, si solo quiere probar el probar la aplicación, vaya directamente al paso 7.

## 1. Arquitectura de la Solución

La solución consta de dos contenedores Docker independientes que se comunican a través de una red Docker personalizada, cumpliendo el requisito de no usar `docker-compose`.

* **Red Docker:** Se crea una red tipo *bridge* llamada `traductor-net`. Esto permite que los contenedores se descubran y comuniquen usando sus nombres de host.

* **Contenedor 1: Servidor MLflow (`mlflow-server`)**
    * **Imagen:** `ghcr.io/mlflow/mlflow:latest` (Imagen oficial de MLflow).
    * **Propósito:** Actúa como el servidor central de tracking para registrar todas las interacciones.
    * **Configuración:**
        * Se ejecuta con el nombre de host `mlflow-server`.
        * Expone su puerto interno `5000` al puerto `5000` del host (`-p 5000:5000`), permitiendo el acceso a la UI de MLflow desde el navegador en `http://localhost:5000`.
        * Se monta un volumen de Docker (`mlflow-data`) para persistir los datos de los *runs* aunque el contenedor se detenga o elimine.

* **Contenedor 2: Aplicación Gradio (`traductor-app`)**
    * **Imagen:** `[TU_USUARIO_DOCKERHUB]/traductor-genai:1.0.0` (Imagen personalizada construida localmente).
    * **Propósito:** Sirve la interfaz web de Gradio y contiene la lógica para llamar al modelo GenAI y registrar en MLflow.
    * **Configuración:**
        * Expone su puerto interno `7860` al puerto `7860` del host (`-p 7860:7860`), permitiendo el acceso a la app Gradio en `http://localhost:7860`.
        * Se conecta a la misma red `traductor-net`.

## 2. Manejo de Claves API (Variables de Entorno)

Como requisito obligatorio, la clave de API **no está** incluida en la imagen de Docker. Se inyecta en el contenedor en el momento de la ejecución usando variables de entorno (`-e`):

1.  `GEMINI_API_KEY`: Pasa la clave de la API de GenAI (Gemini) al script `app.py`.
2.  `MLFLOW_TRACKING_URI`: Informa a la aplicación `app.py` dónde encontrar el servidor MLflow. Se usa el nombre del contenedor: `http://mlflow-server:5000`.

## 3. Comandos Principales (Build, Run, Push)

A continuación, se presentan los comandos exactos para construir, ejecutar y publicar la solución.

### Paso 1: Crear la Red Docker

```bash
docker network create <nombre_de_red>
```

# Paso 2: Crear un volumen para que los datos de MLflow no se pierdan
```bash
docker volume create <nombre_volumen>
```

# Paso 3: Creamos el contenedor con la imagen oficial de MLFLOW.
# Ejecutar el servidor MLflow en segundo plano (-d)
# Añadimos --allowed-hosts "*" (comodín) para aceptar todas las conexiones
```bash
docker run -d \
--name <nombre_del_contenedor> \
--network <nombre_de_red> \
-v <nombre_volumen>:/mlflow \
-p 5000:5000 \
ghcr.io/mlflow/mlflow:latest \
mlflow server \
    --host 0.0.0.0 \
    --port 5000 \
    --backend-store-uri /mlflow \
    --allowed-hosts "*"
```

# Paso 4: Construimos la imagen de la app de gradio
```bash
docker build -t <tu_usuario_docker>/traductor-genai:1.0.0 .
```

# Paso 5: Ejecutar (crear el contenedor) de la app de gradio (localmente)
```bash
export MI_API_KEY="tu_clave_de_gemini_aqui"

docker run -d \
  --name <nombre_contenedor> \
  --network <nombre_de_red> \
  -p 7860:7860 \
  -e GEMINI_API_KEY=$MI_API_KEY \
  -e MLFLOW_TRACKING_URI="http://<nombre_contenedor_mlflow>:5000" \
  <tu_usuario_docker>/traductor-genai:1.0.0
```

# Paso 6: Publicación en Docker Hub
```bash
# 1. Iniciar sesión (pedirá tu usuario y contraseña)
docker login

# 2. (Opcional) Re-taggear la imagen si no usaste tu usuario en el build
docker tag mi-imagen:local <tu_usuario_docker>/traductor-genai:1.0.0

# 3. Subir la imagen
docker push <tu_usuario_docker>/traductor-genai:1.0.0
```

# Imagen en Docker Hub
![Docker Hub](https://drive.google.com/uc?export=view&id=1HvDYLmiYJapPtBdUNrG5KAm5fsOCJfmb)

# Paso 7: Ejecución remota

## Tags

Para hacer el pull tiene los siguientes tags

- 1.0.0
- 1.0.2


```bash
# 1. Descargar la imagen desde Docker Hub
docker pull viraviut/genai-translate:<tag_a_usar>

# 2. Crear la red en docker
docker network create <nombre_de_red>

# 3. Ejecutar el contenedor de MLFLOW
docker run -d \
--name <nombre_del_contenedor> \
--network <nombre_de_red> \
-v <nombre_volumen>:/mlflow \
-p 5000:5000 \
ghcr.io/mlflow/mlflow:latest \
mlflow server \
    --host 0.0.0.0 \
    --port 5000 \
    --backend-store-uri /mlflow \
    --allowed-hosts "*"

# 4. Ejecutar la imagen descargada (Necesitarás crear la red y correr MLflow si es una máquina limpia)

export MI_API_KEY="tu_clave_de_gemini_aqui"

docker run -d \
  --name <nombre_del_contenedor> \
  --network <nombre_de_red> \
  -p 7860:7860 \
  -e GEMINI_API_KEY=$MI_API_KEY \
  -e MLFLOW_TRACKING_URI="http://<nombre_contenedor_mlflow>:5000" \
  viraviut/genai-translate:<tag_a_usar>
```

Si el paso anterior se completó sin ningún inconveniente, debería de ver dos contenedores en la aplicación Docker Desktop
![Docker Desktop](https://drive.google.com/uc?export=view&id=1FRXZbScZR4PTloxcJghc8cIvrKfjaZYQ)
Para abrir la aplicación solo tienes que abrir las direcciones
    - Gradio (`localhost:7860`)
    - MLFLOW (`localhost:5000`)
En tu navegador de preferencia, o hacer click donde aparecen los puertos en los contenedores de docker

# Recopilatorio de fotos del programa funcionando

# Gradio app
![App Gradio Ejecutando](https://drive.google.com/uc?export=view&id=13it2xQj7AYRmIVcOCsIbvH3M6zPOm1gr)

# MLFLOW UI
![MLFLOW UI](https://drive.google.com/uc?export=view&id=1ak2t-DdLa_ZFdTUZyIdEaxaUGr3vbv86)

# VARIAS RUNS
![VARIAS RUNS](https://drive.google.com/uc?export=view&id=1ZXjUwEVBHX0DtZmvzCgdZMsrSvldOQmm)

# INFO RUN
![INFO RUN UNICA](https://drive.google.com/uc?export=view&id=1Ow5-oP38P6WoXRjJM6PdfDEdG06F49Y_)

# METRICAS DE UNA RUN
![METRICAS DE UNA RUN](https://drive.google.com/uc?export=view&id=1enVelNm59fZNIEe892_JrWTvw8vK6b96)

# ARTIFACT PETICION
![ARTIFACT TEXTO A TRADUCIR](https://drive.google.com/uc?export=view&id=1oZd7dF1h-UNXY_SIQjtazpKE5eUPhxxP)

# ARTIFACT RESPUESTA
![ARTIFACT TEXTO TRADUCIDO](https://drive.google.com/uc?export=view&id=1buCX5EDRgW2XAxPljaEr2Tlu9LwB5wOb)

## Authors

- [@viraviutt](https://www.github.com/viraviutt)
- [@akiii-lab](https://www.github.com/akiii-lab)