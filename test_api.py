from dotenv import load_dotenv
import os
from openai import OpenAI

# Cargar .env
load_dotenv(override=True)

api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
print("Prefijo de la API Key cargada:", api_key[:12] if api_key else "(ninguna)")

if not api_key or api_key.lower().startswith("tu_api_key"):
    raise RuntimeError("❌ No hay una API key válida. Revisa tu .env")

# Crear cliente
client = OpenAI(api_key=api_key, timeout=30)

# Hacer una llamada muy simple
resp = client.chat.completions.create(
    model="gpt-4o-mini",  # rápido y barato
    messages=[{"role": "user", "content": "Di solo: Hola, funciona"}],
    temperature=0
)

print("✅ Respuesta del modelo:", resp.choices[0].message.content)
