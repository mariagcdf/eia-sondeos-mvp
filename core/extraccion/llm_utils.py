# core/llm_utils.py
import os, json, re
from typing import Dict, Any, Tuple, Optional
from openai import OpenAI

# ================== Cliente ==================
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

def parse_json_output(raw_text: str):
    """
    Intenta interpretar una salida del modelo como JSON válido.
    Limpia texto fuera de las llaves, elimina bloques de Markdown y devuelve dict si es posible.
    """
    if not raw_text:
        return None

    text = raw_text.strip()

    # 1️⃣ Elimina bloques de código tipo ```json ... ```
    text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"```$", "", text).strip()

    # 2️⃣ Busca el primer bloque JSON entre llaves
    if not text.startswith("{"):
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)

    # 3️⃣ Limpia caracteres invisibles (espacios no imprimibles, BOM, etc.)
    text = text.replace("\u200b", "").replace("\ufeff", "").strip()

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError as e:
        print(f"Error interpretando JSON: {e}")
        print("Salida bruta del modelo:\n", text[:1000], "...")
        return None

# ================== Prompt mejorado ==================
def build_prompt(texto_relevante: str) -> str:
    """
    Extrae localizacion (municipio/provincia/polígono/parcela/RC), parámetros (uso/caudales) y particularidades.
    Regla extra: reconocer patrones 'Vega de Tera (Zamora)', 'término municipal de X', 'provincia de Y'.
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
    instrucciones = """
Reglas:
- Si un dato no aparece, usa null.
- LOCALIZACIÓN:
  • 'municipio': nombres como 'Vega de Tera', 'Junquera de Tera', "Mogarraz" etc.
  • 'provincia': reconoce patrones '(... provincia de X ...)', 'provincia de X', o 'Municipio (Provincia)' p.ej. 'Vega de Tera (Zamora)'.
  • 'poligono'/'parcela'/RC: leer si aparece como 'Polígono 1 Parcela 2621', 'Ref. Catastral 123...', etc.
- USO: 'uso_previsto' conciso ('abastecimiento municipal', 'riego agrícola', ...). 'detalles_de_uso' conserva el matiz textual.
- CAUDALES:
  * 'caudal_max_instantaneo_l_s': valor en L/s del caudal máximo instantáneo (patrones: “Caudal máximo instantáneo”, “QMi”, “Q M i”, “Q máx.”, “Qmax”). Si hay varios (sondeo nuevo/existente), toma el MAYOR.
  * 'caudal_minimo_l_s': solo si está explícito como mínimo (p.ej. “Caudal mínimo”, “Qmín”).
  * Nunca usar 'Caudal medio equivalente (Q_meq)' para estos campos.
  * Devuelve como número con punto decimal (0,83 -> 0.83).
- Devuelve EXCLUSIVAMENTE un JSON válido con el esquema indicado.
Ejemplos de reconocimiento de municipio/provincia:
- "Vega de Tera (Zamora)"  -> municipio="Vega de Tera", provincia="Zamora"
- "término municipal de Junquera de Tera, provincia de Zamora" -> municipio="Junquera de Tera", provincia="Zamora"
- "situado en ... , Zamora" cuando el municipio está claro en la misma oración -> provincia="Zamora"
""".strip()

    return f"""
Eres un asistente técnico. Devuelve EXCLUSIVAMENTE un JSON válido con este esquema:
{json.dumps(schema, ensure_ascii=False, indent=2)}

{instrucciones}

TEXTO:
{texto_relevante}
""".strip()

# ================== Fallback regex localización ==================
_MUNICIPIO_HINTS = [
    r"t[eé]rmino\s+municipal\s+de\s+([A-ZÁÉÍÓÚÑ][\w\s\-’'ªºáéíóúñ]+)",
    r"municipio\s+de\s+([A-ZÁÉÍÓÚÑ][\w\s\-’'ªºáéíóúñ]+)",
    r"\b([A-ZÁÉÍÓÚÑ][\w\s\-’'ªºáéíóúñ]+)\s*\(\s*[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+?\s*\)",  # 'Vega de Tera (Zamora)'
]
_PROVINCIA_HINTS = [
    r"provincia\s+de\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)",
    r"\(\s*([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s*\)",  # paréntesis tras municipio
    r",\s*([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\b"       # coma-Provincia (si contexto de municipio claro)
]

def _clean(s: Optional[str]) -> str:
    return (s or "").strip().strip(",.;:()[]{} ").replace("\u00AD", "")

def _regex_localizacion(texto: str) -> Tuple[str, str]:
    t = texto or ""
    municipio, provincia = "", ""

    # 1) municipio (varios patrones)
    for pat in _MUNICIPIO_HINTS:
        m = re.search(pat, t, flags=re.IGNORECASE)
        if m:
            municipio = _clean(m.group(1))
            # normaliza título de palabras simples
            break

    # 2) provincia (varios patrones)
    for pat in _PROVINCIA_HINTS:
        m = re.search(pat, t, flags=re.IGNORECASE)
        if m:
            provincia = _clean(m.group(1))
            break

    # Heurística: si encontramos "Municipio (Provincia)" en una sola captura (pat 3 de municipio)
    if not provincia and municipio:
        m = re.search(rf"{re.escape(municipio)}\s*\(\s*([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s*\)", t)
        if m:
            provincia = _clean(m.group(1))

    return municipio, provincia

# ================== Llamada con fallback ==================
def call_llm_extract_json(prompt: str, model: str = "gpt-4.1-mini", texto_relevante: Optional[str] = None) -> Dict[str, Any]:
    """
    Ejecuta el prompt y devuelve dict.
    Si 'municipio' o 'provincia' vienen vacíos, intenta inferirlos por regex usando 'texto_relevante'.
    """
    raw = llm_chat(prompt, model=model, temperature=0)
    data = parse_json_output(raw)
    if not data:
        raise ValueError("La salida del modelo no es JSON válido. Revisa el prompt o el texto.")

    # Asegura estructuras
    data.setdefault("localizacion", {})
    loc = data["localizacion"] or {}
    muni = _clean(loc.get("municipio"))
    prov = _clean(loc.get("provincia"))

    if (not muni or not prov) and texto_relevante:
        muni_rx, prov_rx = _regex_localizacion(texto_relevante)
        # completa solo los que falten
        if not muni and muni_rx:
            loc["municipio"] = muni_rx
        if not prov and prov_rx:
            loc["provincia"] = prov_rx
        data["localizacion"] = loc

    return data

# ================== Merge con regex mínimo ==================
def merge_min(datos_llm: dict, datos_regex: dict) -> dict:
    """
    Fusiona IA (LLM) con regex. Prioriza regex en coordenadas/números cuando estén;
    en caudales confía más en LLM si los trae. Completa estructuras vacías.
    """
    if not isinstance(datos_llm, dict):
        datos_llm = {}
    if not isinstance(datos_regex, dict):
        datos_regex = {}

    merged = datos_llm.copy()

    # estructuras base
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

    # Caudales: confía más en LLM si existen
    llm_params = merged.get("parametros", {}) or {}
    for key in ["caudal_max_instantaneo_l_s", "caudal_minimo_l_s"]:
        v = (datos_llm.get("parametros", {}) or {}).get(key)
        if v not in (None, "", []):
            llm_params[key] = v
    merged["parametros"] = llm_params

    return merged
