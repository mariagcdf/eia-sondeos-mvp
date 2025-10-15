import json
import sys
from pathlib import Path
from core.extraccion.llm_utils import call_llm_structured_json

def step(msg: str):
    print(f"MB_STEP: {msg}", flush=True)

def warn(msg: str):
    print(f"MB_WARN: {msg}", flush=True)

# 1. Verificar argumento de entrada
if len(sys.argv) < 2:
    print("Uso: python medio_biotico_no_red_natura.py <ruta_json>", flush=True)
    sys.exit(1)

json_path = Path(sys.argv[1])
if not json_path.exists():
    print(f"El archivo {json_path} no existe.", flush=True)
    sys.exit(1)

step(f"Leyendo JSON: {json_path.name}")

# 2. Cargar JSON existente
try:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
except Exception as e:
    print(f"MB_ERR: No se pudo leer el JSON ({e})", flush=True)
    sys.exit(1)

municipio = data.get("municipio", "municipio no especificado")
provincia = data.get("provincia", "")
uso_suelo = data.get("PH_usos_actuales", "") or data.get("usos_actuales_llm", "")
geologia = data.get("geologia", "")
coordenadas = f"UTM X={data.get('utm_x_principal')}, Y={data.get('utm_y_principal')}"

# 3. Construir prompt contextual
prompt = f"""
Eres un redactor técnico especializado en medio ambiente.
Redacta los tres apartados 4.3, 4.4 y 4.5 de un Estudio de Impacto Ambiental Simplificado
para un sondeo de captación de agua subterránea ubicado en {municipio} ({provincia}), {coordenadas}.

El área no pertenece a la Red Natura 2000 y se encuentra en entorno rural.
Utiliza un estilo técnico, conciso y objetivo. Basándote en los datos del proyecto:

- Geología: {geologia[:600]}
- Usos actuales del suelo: {uso_suelo[:600]}

Devuelve exclusivamente un JSON con este formato:
{{
 "4.3_Medio_biotico": "...",
 "4.4_Medio_perceptual": "...",
 "4.5_Medio_socioeconomico": "..."
}}
"""

# 4. Llamada al modelo
step("Llamando al modelo para redactar 4.3, 4.4 y 4.5...")
try:
    res = call_llm_structured_json(prompt, model="gpt-4.1-mini")
    medio_biotico = res.get("4.3_Medio_biotico", "").strip()
    medio_perceptual = res.get("4.4_Medio_perceptual", "").strip()
    medio_socioeconomico = res.get("4.5_Medio_socioeconomico", "").strip()
    step("Respuesta del modelo recibida y parseada correctamente.")
except Exception as e:
    warn(f"No se pudo obtener respuesta del modelo: {e}")
    sys.exit(1)

# 5. Validar contenido y actualizar el JSON
if not (medio_biotico and medio_perceptual and medio_socioeconomico):
    warn("Alguno de los apartados llegó vacío. No se modifica el JSON.")
    sys.exit(1)

data["4.3_Medio_biotico"] = medio_biotico
data["4.4_Medio_perceptual"] = medio_perceptual
data["4.5_Medio_socioeconomico"] = medio_socioeconomico

# 6. Guardar cambios
try:
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    step("JSON actualizado correctamente con los apartados 4.3, 4.4 y 4.5.")
except Exception as e:
    print(f"MB_ERR: No se pudo escribir en el JSON ({e})", flush=True)
    sys.exit(1)
