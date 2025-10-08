# core/sintesis/alternativas_llm.py
import json
from core.llm_utils import get_client

def redactar_alternativas_struct(datos_min: dict,
                                 model: str = "gpt-4.1-mini",
                                 min_desc_chars: int = 200,
                                 min_val_chars: int  = 400,
                                 min_just_chars: int = 300,
                                 max_retries: int = 3) -> dict:
    """
    Genera Alternativas (cap. 3) con IA, validando JSON y longitud mínima.
    Reintenta y hace una pasada de 'mejora' si queda corto.
    Devuelve SIEMPRE las 3 claves: desc_md, val, just.
    """
    client = get_client()

    p   = (datos_min.get("parametros") or {})
    loc = (datos_min.get("localizacion") or {})

    uso     = p.get("uso_previsto") or "abastecimiento"
    detalles= p.get("detalles_de_uso") or ""
    prof    = p.get("profundidad_proyectada_m") or "desconocida"
    d_ini   = p.get("diametro_perforacion_inicial_mm") or "—"
    d_def   = p.get("diametro_perforacion_definitivo_mm") or "—"
    muni    = loc.get("municipio") or "el municipio"
    prov    = loc.get("provincia") or ""

    schema = {"desc_md":"string","val":"string","just":"string"}

    base_prompt = f"""
Eres redactor técnico de EIAs. Redacta el CAP. 3 (Alternativas) para un sondeo de aguas en {muni} ({prov}).
USO PREVISTO: {uso}. Detalles de uso: {detalles}
Datos técnicos: profundidad {prof} m (aprox.), Ø inicial {d_ini} mm, Ø definitivo {d_def} mm.

SALIDA: EXCLUSIVAMENTE JSON con este esquema (sin texto extra):
{json.dumps(schema, ensure_ascii=False)}

CONTENIDO:
- "desc_md": sección 3.1 como VIÑETAS en Markdown (guion '-'), con estas 6 alternativas SIEMPRE en ESTE orden y con estos títulos exactos:
  - Alternativa 0 - No actuación
  - Alternativa 1 - Sondeo
  - Alternativa 2 - Pozo tradicional
  - Alternativa 3 - Captación superficial
  - Alternativa 4 - Transporte mediante cubas
  - Alternativa 5 - Conexión a la red municipal
  Cada viñeta: 3-4 líneas, lenguaje técnico claro, vinculando el análisis al USO PREVISTO cuando proceda.
- "val": 3.2 Valoración técnica, económica y ambiental, 8-12 líneas, texto corrido. Explica por qué se descartan las no elegidas respecto al USO PREVISTO.
- "just": 3.3 Justificación de la alternativa elegida (sondeo), 6-10 líneas, centrada en el USO PREVISTO y la viabilidad técnico-ambiental.

Estilo: español (España), formal, técnico-administrativo, sin florituras ni cifras inventadas, teniendo muy en cuenta el dato que has obtenido sobre el uso previsto para el agua extraida.
No escribas nada fuera del JSON.
""".strip()

    def _safe_json(s: str) -> dict:
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            b, e = s.find("{"), s.rfind("}")
            if b != -1 and e != -1 and e > b:
                return json.loads(s[b:e+1])
            return {"desc_md":"", "val":"", "just":""}

    def _ok_len(x: str, n: int) -> bool:
        return bool(x) and len(x.strip()) >= n

    best = {"desc_md":"", "val":"", "just":""}
    last_err = None

    for _ in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": base_prompt}],
                temperature=0.3,
            )
            raw = (resp.choices[0].message.content or "").strip()
            data = _safe_json(raw)
        except Exception as e:
            last_err = str(e)
            continue

        desc = (data.get("desc_md") or "").strip()
        val  = (data.get("val") or "").strip()
        just = (data.get("just") or "").strip()

        if _ok_len(desc, min_desc_chars) and _ok_len(val, min_val_chars) and _ok_len(just, min_just_chars):
            return {"desc_md": desc, "val": val, "just": just}

        if len(desc) + len(val) + len(just) > len(best["desc_md"]) + len(best["val"]) + len(best["just"]):
            best = {"desc_md": desc, "val": val, "just": just}

        need = []
        if not _ok_len(desc, min_desc_chars): need.append("desc_md")
        if not _ok_len(val,  min_val_chars):  need.append("val")
        if not _ok_len(just, min_just_chars): need.append("just")

        improve_prompt = f"""
Mejora este JSON de alternativas para un EIA (sin cambiar claves ni estructura).
Amplía y concreta con foco en el USO PREVISTO: {uso}.
Campos a ampliar: {", ".join(need)}.
Responde SOLO con JSON.

JSON actual:
{json.dumps({"desc_md": desc, "val": val, "just": just}, ensure_ascii=False)}
""".strip()

        try:
            resp2 = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": improve_prompt}],
                temperature=0.2,
            )
            raw2 = (resp2.choices[0].message.content or "").strip()
            data2 = _safe_json(raw2)
            desc2 = (data2.get("desc_md") or desc).strip()
            val2  = (data2.get("val")     or val).strip()
            just2 = (data2.get("just")    or just).strip()
            if _ok_len(desc2, min_desc_chars) and _ok_len(val2, min_val_chars) and _ok_len(just2, min_just_chars):
                return {"desc_md": desc2, "val": val2, "just": just2}
            if len(desc2) + len(val2) + len(just2) > len(best["desc_md"]) + len(best["val"]) + len(best["just"]):
                best = {"desc_md": desc2, "val": val2, "just": just2}
        except Exception as e:
            last_err = str(e)
            continue

    out = {
        "desc_md": best["desc_md"].strip(),
        "val":     best["val"].strip(),
        "just":    best["just"].strip(),
    }
    if last_err:
        out["_error"] = last_err
    return out


def generar_alternativas_llm(datos_min: dict) -> dict:
    """Devuelve los 3 placeholders listos para DOCX."""
    s = redactar_alternativas_struct(datos_min)
    return {
        "PH_Alternativas_Desc": (s.get("desc_md") or "").strip(),
        "PH_Alternativas_Val":  (s.get("val") or "").strip(),
        "PH_Alternativas_Just": (s.get("just") or "").strip(),
    }
