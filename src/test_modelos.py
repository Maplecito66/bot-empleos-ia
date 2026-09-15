import os
from dotenv import load_dotenv
from google import genai

# Cargar las variables de entorno
directorio_actual = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(directorio_actual, ".env"))

# Extraer la primera clave disponible
claves_str = os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY")
if not claves_str:
    print("❌ No se encontró ninguna API Key en el archivo .env")
    exit()

clave = [k.strip() for k in claves_str.split(',') if k.strip()][0]

try:
    client = genai.Client(api_key=clave)
    print("🔍 Consultando servidores de Google...\n")
    print("✅ Modelos habilitados para tu API Key:")

    for model in client.models.list():
        print(f" - {model.name}")
except Exception as e:
    print(f"🚨 Error al conectar: {e}")