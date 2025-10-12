import os, json, unicodedata, re
from typing import Dict, Any, Optional

# --- utilidades básicas ---
def _strip_accents(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s))
    return "".join(ch for ch in s if not unicodedata.combining(ch))

def _norm_key(s: str) -> str:
    s = _strip_accents(s).lower().strip()
    s = s.replace(" ", "_")
    s = re.sub(r"[^\w\.]", "", s)
    return s

def _flatten(d: Dict[str, Any], parent: str = "", sep: str = ".") -> Dict[str, Any]:
    out = {}
    for k, v in (d or {}).items():
        k = str(k)
        key = f"{parent}{sep}{k}" if parent else k
        if isinstance(v, dict):
            out.update(_flatten(v, key, sep))
        else:
            out[key] = v
    return out

def _fmt_num(v) -> str:
    if v in (None, "", []):
        return ""
    try:
        f = float(v)
        return str(int(f)) if abs(f - int(f)) < 1e-9 else str(f)
    except Exception:
        return str(v)

def _best(*vals) -> str:
    cand = [str(v) for v in vals if v not in (None, "", [])]
    if not cand:
        return ""
    return max(cand, key=lambda x: (len(x.strip()), -cand.index(x)))

def _table_from_coords(coords: Dict[str, Any]) -> str:
    utm = (coords.get("utm") or {})
    geo = (coords.get("geo") or {})
    lines = [
        f"UTM X: {_fmt_num(utm.get('x'))}",
        f"UTM Y: {_fmt_num(utm.get('y'))}",
        f"Huso: {utm.get('huso') or '—'}",
        f"Datum: {utm.get('datum') or '—'}",
    ]
    if geo.get("lat") or geo.get("lon"):
        lines.append(f"Latitud: {geo.get('lat') or '—'}")
        lines.append(f"Longitud: {geo.get('lon') or '—'}")
    return "\n".join(lines).strip()

# --- formateador avanzado para PH_Consumo ---
def _format_consumo(text: str) -> str:
    """Limpia y formatea el bloque de consumo: elimina títulos, añade saltos y negritas automáticas."""
    if not text:
        return ""

    s = re.sub(r"[ \t]+", " ", text)
    s = re.sub(r"\n{2,}", "\n", s).strip()

    # Elimina encabezados tipo "3.1. Caudal necesario"
    s = re.sub(
        r"^\s*(\d+[.,]?\d*\s*)?(Caudal\s+necesario)\s*[:\-–—]?\s*",
        "",
        s,
        flags=re.IGNORECASE
    )

    # Añade saltos dobles antes de bloques relevantes
    patrones_salto = [
        r"(?=\bConsumos\s*:)",
        r"(?=\bEl\s+reparto)",
        r"(?=\bSondeo\s+(nuevo|existente))",
        r"(?=\bPozo\s+existente)",
        r"(?=\bNOTA\s*:)",
    ]
    for pat in patrones_salto:
        s = re.sub(pat, "\n\n", s, flags=re.IGNORECASE)

    # Negritas automáticas
    reemplazos_negrita = {
        r"\b(Consumos\s*:)"           : r"<b>\1</b>",
        r"\b(Sondeo\s+nuevo\s*:?)"    : r"<b>\1</b>",
        r"\b(Sondeo\s+existente\s*:?)": r"<b>\1</b>",
        r"\b(Pozo\s+existente\s*:?)"  : r"<b>\1</b>",
        r"\b(NOTA\s*:)"               : r"<b>\1</b>",
    }
    for pat, rep in reemplazos_negrita.items():
        s = re.sub(pat, rep, s, flags=re.IGNORECASE)

    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

# --- núcleo principal ---
def build_global_placeholders(
    texto_relevante: str,
    texto_completo_pdf: str,
    datos_regex_min: Dict[str, Any],
    *,
    save_to: Optional[str] = None,
    model: str = "gpt-4.1-mini"
) -> Dict[str, str]:
    """
    Devuelve un dict {placeholder: valor} limpio y coherente con la plantilla.
    """
    from core.extraccion.llm_utils import build_prompt, call_llm_extract_json, merge_min
    from core.extraccion.bloques_textuales import extraer_bloques_literal

    # 1) LLM estructurado
    prompt = build_prompt(texto_relevante)
    datos_llm = call_llm_extract_json(prompt, model=model, texto_relevante=texto_relevante)

    # 2) Bloques literales
    bloques = extraer_bloques_literal(texto_completo_pdf)

    # 3) Merge LLM + regex
    merged = merge_min(datos_llm, datos_regex_min)

    # 4) Accesos cómodos
    P = merged.get("parametros", {}) or {}
    L = merged.get("localizacion", {}) or {}
    C = merged.get("coordenadas", {}) or {}
    UTM = (C.get("utm") or {})
    GEO = (C.get("geo") or {})
    FLAGS = (merged.get("flags") or {})

    # 5) Coalescencia de bloques
    PH_Antecedentes = bloques.get("PH_Antecedentes", "")
    PH_Localizacion = bloques.get("PH_Localizacion", "") or bloques.get("PH_Situacion", "")
    PH_Consumo = _format_consumo(bloques.get("PH_Consumo", ""))
    geologia = bloques.get("geologia", "") or bloques.get("geología", "")

    # 6) Construcción del JSON de placeholders
    placeholders: Dict[str, str] = {
        "PH_Antecedentes": PH_Antecedentes,
        "PH_Localizacion": PH_Localizacion,
        "PH_Consumo": PH_Consumo,
        "geologia": geologia,
        # --- coordenadas ---
        "utm_x_principal": _fmt_num(_best(UTM.get("x"), C.get("x"))),
        "utm_y_principal": _fmt_num(_best(UTM.get("y"), C.get("y"))),
        "utm_huso_principal": _best(UTM.get("huso"), C.get("huso")),
        "geo_lat_principal": _best(GEO.get("lat"), C.get("lat")),
        "geo_lon_principal": _best(GEO.get("lon"), C.get("lon")),
        # --- datos generales ---
        "municipio": _best(L.get("municipio")),
        "provincia": _best(L.get("provincia")),
        "profundidad": _fmt_num(_best(P.get("profundidad"), P.get("profundidad_proyectada_m"))),
        "diametro_inicial": _fmt_num(P.get("diametro_inicial")),
        "diametro_perforacion_inicial_mm": _fmt_num(P.get("diametro_perforacion_inicial_mm")),
        "caudal_max_instantaneo_l_s": _fmt_num(P.get("caudal_max_instantaneo_l_s")),
        "instalacion_electrica": _best(P.get("instalacion_electrica")),
        "potencia_bombeo_kw": _fmt_num(P.get("potencia_bombeo_kw")),
        # --- avisos ---
        "aviso_existente": (
            "⚠ Se ha detectado un SONDEO EXISTENTE en el documento. "
            "Recuerda copiar manualmente la parte referida al sondeo existente."
            if FLAGS.get("hay_sondeo_existente") else ""
        ),
        # --- CLAVES DE ALTERNATIVAS ---
        "PH_Alternativas_Desc": "",
        "PH_Alternativas_Val": "",
        "PH_Alternativas_Just": "",
    }

    # 7) Aplanado completo para depuración
    flat_all = _flatten(merged)

    # 8) Guardado limpio
    if save_to:
        os.makedirs(os.path.dirname(save_to), exist_ok=True) if os.path.dirname(save_to) else None
        clean_out = {**placeholders, **flat_all}
        with open(save_to, "w", encoding="utf-8") as f:
            json.dump(clean_out, f, ensure_ascii=False, indent=2)

    return placeholders


# --- helper simple por si quieres solo “JSON de placeholders a disco” ---
def build_and_save_global_placeholders(
    texto_relevante: str,
    texto_completo_pdf: str,
    datos_regex_min: Dict[str, Any],
    out_json_path: str,
    model: str = "gpt-4.1-mini"
) -> str:
    ph = build_global_placeholders(
        texto_relevante=texto_relevante,
        texto_completo_pdf=texto_completo_pdf,
        datos_regex_min=datos_regex_min,
        save_to=out_json_path,
        model=model
    )
    return out_json_path
