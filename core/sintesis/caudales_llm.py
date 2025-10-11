# core/sintesis/caudales_llm.py
import json
from typing import Dict, Any
from core.extraccion.llm_utils import llm_chat, parse_json_output


def extract_caudales_from_text(texto_full: str, model: str = "gpt-4.1-mini") -> Dict[str, Any]:
    """
    Extrae caudales con LLM sobre TODO el texto:
    - 'caudal_max_instantaneo_l_s': toma el MAYOR valor asociado a 'Caudal máximo instantáneo', 'QMi', 'Q M i', 'Q máx.', 'Qmax'.
    - 'caudal_minimo_l_s': solo si aparece explícito (Qmín., caudal mínimo).
    - Nunca usa 'Caudal medio equivalente (Q_meq)'.
    Devuelve: {"parametros": {"caudal_max_instantaneo_l_s": float|None, "caudal_minimo_l_s": float|None}}
    """
    schema = {
        "parametros": {
            "caudal_max_instantaneo_l_s": "number|null",
            "caudal_minimo_l_s": "number|null"
        }
    }
    prompt = f"""
Eres un asistente técnico. Devuelve EXCLUSIVAMENTE un JSON válido con este esquema:
{json.dumps(schema, ensure_ascii=False, indent=2)}

Reglas:
- Busca caudales en L/s.
- 'caudal_max_instantaneo_l_s': toma el MAYOR valor asociado a 'Caudal máximo instantáneo', 'QMi', 'Q M i', 'Q máx.', 'Qmax'.
- 'caudal_minimo_l_s': solo si aparece explícito como 'Caudal mínimo' o 'Qmín.'.
- NUNCA uses 'Caudal medio equivalente (Q_meq)' para estos campos.
- Convierte a número con punto decimal (0,83 -> 0.83).
- Devuelve SOLO el JSON.

TEXTO:
{texto_full[:22000]}
""".strip()

    raw = llm_chat(prompt, model=model, temperature=0)
    data = parse_json_output(raw) or {}

    p = (data.get("parametros") or {})

    def _norm(x):
        if x is None:
            return None
        try:
            return float(str(x).replace(",", "."))
        except Exception:
            return None

    return {
        "parametros": {
            "caudal_max_instantaneo_l_s": _norm(p.get("caudal_max_instantaneo_l_s")),
            "caudal_minimo_l_s":          _norm(p.get("caudal_minimo_l_s")),
        }
    }


def redactar_caudal_llm(datos_min: dict) -> str:
    """
    Redacta el apartado '3.1. Caudal necesario' (texto) de la EIA, basándose en los datos reales.
    Usa el caudal máximo extraído por la IA o por regex (ya presente en datos_min), y el uso previsto.
    """
    p = (datos_min.get("parametros") or {})
    uso     = p.get("uso_previsto", "abastecimiento municipal")
    detalle = p.get("detalles_de_uso", "")
    qmax    = p.get("caudal_max_instantaneo_l_s", None)

    prompt = f"""
Eres un redactor técnico especializado en Evaluaciones de Impacto Ambiental.

Redacta el apartado **3.1. Caudal necesario** de una EIA de un sondeo de aguas subterráneas.
USO PREVISTO: {uso}
DETALLES: {detalle}
Caudal máximo instantáneo (si disponible): {qmax} L/s

Debe explicar, en 5–7 líneas:
- Cómo se estima el caudal necesario en función de la demanda/consumo y el USO PREVISTO (m³/año ↔ L/s, Q media y Q máx).
- Qué hipótesis típicas se aplican y cómo se valida frente a condicionantes del Organismo de Cuenca (distancias mínimas, limitaciones de bombeo, etc.).
- Mantén tono técnico-administrativo (España). NO inventes cifras si no hay dato.

Entrega un ÚNICO PÁRRAFO (sin títulos ni viñetas).
""".strip()

    return llm_chat(prompt)
