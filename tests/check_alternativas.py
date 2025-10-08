# check_alternativas_llm.py
import os, json
from core.sintesis.alternativas_llm import generar_alternativas_llm
from dotenv import load_dotenv
load_dotenv()


if not os.getenv("OPENAI_API_KEY"):
    raise SystemExit("❌ Falta OPENAI_API_KEY")

datos_min = {
    "localizacion": {"municipio": "Carrascal del Obispo", "provincia": "Salamanca"},
    "parametros": {
        "uso_previsto": "abastecimiento municipal",
        "detalles_de_uso": "Refuerzo del suministro en estiaje",
        "profundidad_proyectada_m": 140,
        "diametro_perforacion_inicial_mm": 215,
        "diametro_perforacion_definitivo_mm": 160,
    }
}

print("▶️ Generando alternativas con IA...\n")
alts = generar_alternativas_llm(datos_min)
print(json.dumps(alts, ensure_ascii=False, indent=2))
