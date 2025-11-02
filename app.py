import gradio as gr
import os
import time
import mlflow
from openai import OpenAI
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# --- Configuración 1: Cliente del Modelo (Gemini) ---

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("Advertencia: La variable de entorno GEMINI_API_KEY no está configurada.")

GEMINI_MODEL = OpenAI(
    api_key=API_KEY,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

# --- Configuración 2: MLflow Tracking (Parte B) ---
# Apuntamos al servidor MLflow que correrá en otro contenedor,
# usaremos el nombre del contenedor 'mlflow-server' como hostname.
# El puerto 5000 es el puerto por defecto de MLflow.
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow-server:5000")
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

# Definimos un nombre para el experimento en MLflow
EXPERIMENT_NAME = "genai-translations"


MODEL_NAME = "gemini-2.5-flash"


try:
    mlflow.set_experiment(EXPERIMENT_NAME)
    print(f"MLflow conectado a: {MLFLOW_TRACKING_URI}")
    print(f"Usando experimento: {EXPERIMENT_NAME}")
except Exception as e:
    print(f"Error conectando a MLflow en {MLFLOW_TRACKING_URI}: {e}")
    print("Asegúrate de que el contenedor de MLflow esté corriendo y en la misma red Docker.")


# --- Lógica de la Aplicación ---

def traducir_y_registrar(texto_fuente, idioma_objetivo):
    """
    Función principal que llama al modelo de GenAI y registra en MLflow.
    """
    if not API_KEY:
        return "[ERROR] La GEMINI_API_KEY no fue proporcionada. El contenedor no puede traducir."

    if not texto_fuente or not idioma_objetivo:
        return "[ERROR] El texto fuente y el idioma objetivo no pueden estar vacíos."

    print(f"Traduciendo '{texto_fuente}' a {idioma_objetivo}...")
    
    # 1. Preparar el prompt para el modelo
    system_prompt = """
                    Eres un traductor profesional experto en lingüística, semántica y contextos culturales. Tu tarea es traducir cualquier texto al idioma solicitado con precisión, naturalidad y el tono adecuado.

                        Reglas de traducción:

                        1. Traduce con fidelidad al significado, tono y registro del texto original.

                        2. Mantén el formato del texto (párrafos, listas, etc.) cuando sea relevante.

                        3. No incluyas explicaciones, introducciones ni conclusiones.

                        4. Si existen varias traducciones posibles, proporciona hasta tres opciones, separadas por punto y coma.

                        5. Cuando des varias opciones, indica brevemente el contexto o registro (por ejemplo, formal, informal, técnico, coloquial).

                        6. Si el texto puede tener distintos significados según el contexto, acláralo en una línea breve, sin extenderte.

                        7.No uses frases como “La traducción es:” o “Aquí tienes la traducción”.

                        8. Si no se especifica el idioma de destino, traduce automáticamente al inglés.
                    """
    user_prompt = f"Traduce el siguiente texto al {idioma_objetivo}: \"{texto_fuente}\""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    # Iniciamos el run de MLflow ANTES de la llamada para capturar todo
    # Usamos 'with' para asegurar que el run se cierre aunque falle
    with mlflow.start_run() as run:
        start_time = time.time()
        
        try:
            # 2. Llamar al modelo GenAI (Gemini)
            resp = GEMINI_MODEL.chat.completions.create(
                model=MODEL_NAME, # Usamos un modelo específico como en tu notebook
                messages=messages
            )
            
            texto_traducido = resp.choices[0].message.content
            
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000
            status = "EXITOSO"

        except Exception as e:
            end_time = time.time()
            latency_ms = (end_time - start_time) * 1000
            texto_traducido = f"[ERROR EN TRADUCCIÓN] {str(e)}"
            status = "FALLIDO"
            print(f"Error en la API: {e}")

        # 3. Registrar en MLflow (Parte B)
        try:
            # Registrar parámetros (inputs)
            mlflow.log_param("idioma_objetivo", idioma_objetivo)
            mlflow.log_param("longitud_fuente", len(texto_fuente))
            mlflow.log_param("texto_fuente", texto_fuente[:250]) # Limitar para UI de MLflow
            mlflow.log_param("modelo_usado", MODEL_NAME)
            mlflow.log_param("status", status)

            # Registrar métricas (outputs)
            mlflow.log_metric("latency_ms", latency_ms)
            mlflow.log_metric("longitud_respuesta", len(texto_traducido))

            # Registrar artefactos (archivos)
            # Guardamos la conversación completa en archivos de texto
            mlflow.log_text(texto_fuente, "texto_fuente.txt")
            mlflow.log_text(texto_traducido, "texto_traducido.txt")
            
            print(f"Run {run.info.run_id} registrado en MLflow con estado: {status}")
        
        except Exception as e:
            print(f"Error al registrar en MLflow: {e}")
            # No relanzamos la excepción, queremos que el usuario vea la traducción
            # incluso si MLflow falla.

        return texto_traducido

# --- Interfaz de Gradio (Parte A) ---

# Lista de idiomas comunes para el selector
idiomas_disponibles = [
    "Inglés", "Español", "Francés", "Alemán", "Italiano", 
    "Portugués", "Japonés", "Chino (Simplificado)", "Coreano", "Ruso"
]

with gr.Blocks(theme=gr.themes.Soft()) as app:
    gr.Markdown(
        """
        # App de Traducción con GenAI, MLflow y Docker
        Ingresa un texto, selecciona el idioma al que quieres traducir y presiona 'Traducir'.
        Cada traducción se registrará automáticamente en el servidor MLflow.
        """
    )
    
    with gr.Row():
        with gr.Column():
            # 1. Input: Texto a traducir
            input_texto = gr.Textbox(
                label="Texto Fuente", 
                placeholder="Escribe el texto que deseas traducir aquí..."
            )
            
            # 2. Input: Idioma objetivo
            input_idioma = gr.Dropdown(
                label="Idioma Objetivo",
                choices=idiomas_disponibles,
                value="Inglés"
            )
            
            btn_traducir = gr.Button("Traducir", variant="primary")
            
        with gr.Column():
            # 3. Output: Traducción
            output_traduccion = gr.Textbox(
                label="Texto Traducido",
                interactive=False # El usuario no puede escribir aquí
            )

    # Aplicar la función y mostrar la traducción
    btn_traducir.click(
        fn=traducir_y_registrar,
        inputs=[input_texto, input_idioma],
        outputs=[output_traduccion]
    )
    
    gr.Markdown(
        f"""
        ---
        * **Servidor MLflow Tracking:** `{MLFLOW_TRACKING_URI}`
        * **Experimento MLflow:** `{EXPERIMENT_NAME}`
        * **Modelo GenAI:** `gemini-2.5-flash`
        """
    )

if __name__ == "__main__":
    # Exponer la app en la red (0.0.0.0) para que sea accesible desde Docker
    # El puerto 7860 es el que expondremos en el Dockerfile
    app.launch(server_name="0.0.0.0", server_port=7860)