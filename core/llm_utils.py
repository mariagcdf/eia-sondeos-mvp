# core/llm_utils.py
import os, json
from openai import OpenAI

def get_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("❌ Falta OPENAI_API_KEY. Crea un .env con la clave.")
    return OpenAI(api_key=api_key)

def llm_chat(prompt: str, model="gpt-4o-mini", temperature=0.3) -> str:
    client = get_client()
    completion = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature
    )
    return completion.choices[0].message.content.strip()

def parse_json_output(raw: str):
    try:
        start, end = raw.find("{"), raw.rfind("}") + 1
        return json.loads(raw[start:end])
    except Exception:
        return {}
    
    # --- COMPAT: extracción estructurada (se mantiene el prompt original) ---

import json  # por si no está ya importado arriba
from typing import Dict, Any  # idem

def build_prompt(texto_relevante: str) -> str:
    """
    Prompt para extraer:
    - localización básica (municipio/provincia, etc.)
    - uso_previsto / detalles_de_uso
    - caudal_max_instantaneo_l_s / caudal_minimo_l_s (la IA debe leerlos, con formatos QMi, Q máx., etc.)
    """
    schema = {
        "id": "string|null",
        "localizacion": {
            "municipio": "string|null",
            "provincia": "string|null",
            "poligono": "string|number|null",
            "parcela": "string|number|null",
            "referencia_catastral": "string|null"
        },
        "parametros": {
            "uso_previsto": "string|null",
            "detalles_de_uso": "string|null",
            "caudal_max_instantaneo_l_s": "number|null",
            "caudal_minimo_l_s": "number|null"
        },
        "particularidades": {
            "numero_sondeos_previstos": "number|null",
            "observaciones": "string|null"
        }
    }
    return f"""
Eres un asistente técnico. Devuelve EXCLUSIVAMENTE un JSON válido con este esquema:
{json.dumps(schema, ensure_ascii=False, indent=2)}

Instrucciones:
- Si un dato no aparece, usa null.
- 'uso_previsto' conciso (p.ej.: 'abastecimiento municipal', 'riego agrícola', 'apoyo a pozo existente').
- 'detalles_de_uso' conserva el matiz exacto del proyecto.
- Para CAUDALES:
  * 'caudal_max_instantaneo_l_s': extrae el valor en L/s del caudal máximo instantáneo. 
    Acepta variantes como “Caudal máximo instantáneo”, “QMi”, “Q M i”, “Q máx.”, “Qmax”.
    Si aparecen varios (p.ej. para sondeo nuevo y pozo existente), toma el MAYOR.
  * 'caudal_minimo_l_s': extrae SOLO si está explícito como mínimo (p.ej. “Caudal mínimo” o “Qmín”).
  * NUNCA uses “Caudal medio equivalente (Q_meq)” para estos campos.
  * Convierte a número con punto decimal (ej: 0,83 -> 0.83).
- Devuelve solo el JSON, sin texto adicional.

TEXTO:
{texto_relevante}
""".strip()

def call_llm_extract_json(prompt: str, model: str = "gpt-4.1-mini") -> Dict[str, Any]:
    """Ejecuta el prompt anterior y devuelve un dict (tolerando «ruido» fuera del JSON)."""
    # usamos la misma conexión que el resto del módulo
    raw = llm_chat(prompt, model=model, temperature=0)
    data = parse_json_output(raw)
    if not data:
        raise ValueError("La salida del modelo no es JSON válido. Revisa el prompt o el texto.")
    return data

# --- COMPAT: extracción estructurada (se mantiene el prompt original) ---

import json  # por si no está ya importado arriba
from typing import Dict, Any  # idem

def build_prompt(texto_relevante: str) -> str:
    """
    Prompt para extraer:
    - localización básica (municipio/provincia, etc.)
    - uso_previsto / detalles_de_uso
    - caudal_max_instantaneo_l_s / caudal_minimo_l_s (la IA debe leerlos, con formatos QMi, Q máx., etc.)
    """
    schema = {
        "id": "string|null",
        "localizacion": {
            "municipio": "string|null",
            "provincia": "string|null",
            "poligono": "string|number|null",
            "parcela": "string|number|null",
            "referencia_catastral": "string|null"
        },
        "parametros": {
            "uso_previsto": "string|null",
            "detalles_de_uso": "string|null",
            "caudal_max_instantaneo_l_s": "number|null",
            "caudal_minimo_l_s": "number|null"
        },
        "particularidades": {
            "numero_sondeos_previstos": "number|null",
            "observaciones": "string|null"
        }
    }
    return f"""
Eres un asistente técnico. Devuelve EXCLUSIVAMENTE un JSON válido con este esquema:
{json.dumps(schema, ensure_ascii=False, indent=2)}

Instrucciones:
- Si un dato no aparece, usa null.
- 'uso_previsto' conciso (p.ej.: 'abastecimiento municipal', 'riego agrícola', 'apoyo a pozo existente').
- 'detalles_de_uso' conserva el matiz exacto del proyecto.
- Para CAUDALES:
  * 'caudal_max_instantaneo_l_s': extrae el valor en L/s del caudal máximo instantáneo. 
    Acepta variantes como “Caudal máximo instantáneo”, “QMi”, “Q M i”, “Q máx.”, “Qmax”.
    Si aparecen varios (p.ej. para sondeo nuevo y pozo existente), toma el MAYOR.
  * 'caudal_minimo_l_s': extrae SOLO si está explícito como mínimo (p.ej. “Caudal mínimo” o “Qmín”).
  * NUNCA uses “Caudal medio equivalente (Q_meq)” para estos campos.
  * Convierte a número con coma decimal (ej: 0.83 -> 0,83).
- Devuelve solo el JSON, sin texto adicional.

TEXTO:
{texto_relevante}
""".strip()

def call_llm_extract_json(prompt: str, model: str = "gpt-4.1-mini") -> Dict[str, Any]:
    """Ejecuta el prompt anterior y devuelve un dict (tolerando «ruido» fuera del JSON)."""
    # usamos la misma conexión que el resto del módulo
    raw = llm_chat(prompt, model=model, temperature=0)
    data = parse_json_output(raw)
    if not data:
        raise ValueError("La salida del modelo no es JSON válido. Revisa el prompt o el texto.")
    return data

def merge_min(datos_llm: dict, datos_regex: dict) -> dict:
    """
    Fusiona los datos extraídos por IA (LLM) con los detectados por regex.
    Prioriza los valores numéricos o coordenadas del regex si existen,
    salvo en los caudales, donde se confía más en la interpretación del LLM.
    Devuelve un dict con secciones: parametros, coordenadas, localizacion, particularidades.
    """
    if not isinstance(datos_llm, dict):
        datos_llm = {}
    if not isinstance(datos_regex, dict):
        datos_regex = {}

    merged = datos_llm.copy()

    # Asegurar estructuras base
    for section in ["parametros", "coordenadas", "localizacion", "particularidades"]:
        if section not in merged or not isinstance(merged[section], dict):
            merged[section] = {}

        src = datos_regex.get(section, {})
        if isinstance(src, dict):
            for k, v in src.items():
                if isinstance(v, dict):
                    merged[section][k] = {**merged[section].get(k, {}), **v}
                elif v not in (None, "", []):
                    merged[section][k] = v

    # Excepción → en caudales confiamos más en IA si los trae
    llm_params = merged.get("parametros", {}) or {}
    for key in ["caudal_max_instantaneo_l_s", "caudal_minimo_l_s"]:
        v = (datos_llm.get("parametros", {}) or {}).get(key)
        if v not in (None, "", []):
            llm_params[key] = v
    merged["parametros"] = llm_params

    return merged

