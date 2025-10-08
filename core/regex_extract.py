# core/regex_extract.py
import re
from typing import Dict, Any, Optional

# ----------------- Helpers -----------------
def _to_float_safe(s: str) -> Optional[float]:
    """Convierte string a float con seguridad (None si falla). Admite coma decimal."""
    try:
        return float(s.replace(",", "."))
    except Exception:
        return None


def _to_float_thousands(s: str) -> Optional[float]:
    """
    Convierte strings con miles+decimales:
    - "4.516.789" -> 4516789
    - "38,1" -> 38.1
    """
    try:
        s = s.strip()
        s = re.sub(r'(?<=\d)\.(?=\d{3}\b)', '', s)  # quita puntos de miles
        s = s.replace(",", ".")
        return float(s)
    except Exception:
        return None


# ----------------- Extractor principal -----------------
def regex_extract_min_fields(text: str) -> Dict[str, Any]:
    """
    Extrae campos numéricos clave del proyecto usando regex.
    Devuelve dict con los valores o None si no se encuentran.
    """
    out: Dict[str, Any] = {
        "parametros": {
            "superficie_parcela_m2": None,
            "profundidad_proyectada_m": None,
            "diametro_perforacion_inicial_mm": None,
            "diametro_perforacion_definitivo_mm": None,
            "diametro_tuberia_impulsion_mm": None,
            "caudal_max_instantaneo_l_s": None,
            "caudal_minimo_l_s": None,
            "potencia_bombeo_kw": None,
        },
        "coordenadas": {
            "utm": {"x": None, "y": None, "huso": None, "datum": None}
        }
    }

    t = text or ""

    # ---------- Superficie ----------
    m = re.search(r'superficie[^0-9]{0,40}(\d[\d\.,]{2,})\s*(m2|m²|m\^2|ha)\b', t, re.I)
    if m:
        val = _to_float_thousands(m.group(1))
        unidad = m.group(2).lower()
        if val is not None:
            out["parametros"]["superficie_parcela_m2"] = int(val * 10000) if "ha" in unidad else int(val)

    # ---------- Coordenadas UTM ----------
    m = re.search(r'\bX\s*=\s*([\d\.,]+)', t)
    if m:
        out["coordenadas"]["utm"]["x"] = _to_float_thousands(m.group(1))
    m = re.search(r'\bY\s*=\s*([\d\.,]+)', t)
    if m:
        out["coordenadas"]["utm"]["y"] = _to_float_thousands(m.group(1))
    m = re.search(r'\bHuso\s*(\d{1,2})\b', t, re.I)
    if m:
        out["coordenadas"]["utm"]["huso"] = m.group(1)
    m = re.search(r'(ETRS[- ]?89|ED50|WGS[- ]?84)', t, re.I)
    if m:
        out["coordenadas"]["utm"]["datum"] = m.group(1).upper().replace(" ", "")

    # ---------- Profundidad (m, no mm) ----------
    m = re.search(
        r'(profundidad\s+(proyectada|prevista)|longitud\s+(del\s+)?sondeo)[\s\S]{0,160}?'
        r'(\d{1,4}(?:[.,]\d+)?)\s*m(?!m)\b',
        t, re.I
    )
    if m:
        out["parametros"]["profundidad_proyectada_m"] = _to_float_safe(m.group(4))

    # ---------- Diámetros ----------
    m_def = re.search(
        r'definitivo\s+de\s+la\s+entubaci[oó]n[\s\S]{0,240}?ser[aá]\s+de\s+(\d{2,3}(?:[.,]\d+)?)\s*mm',
        t, re.I
    )
    if m_def:
        out["parametros"]["diametro_perforacion_definitivo_mm"] = _to_float_safe(m_def.group(1))

    m_ini = re.search(
        r'di[aá]metro\s+inicial[\s\S]{0,240}?ser[aá]\s+(?:como\s+)?m[ií]nimo\s+de\s+(\d{2,3}(?:[.,]\d+)?)\s*mm',
        t, re.I
    )
    if m_ini:
        out["parametros"]["diametro_perforacion_inicial_mm"] = _to_float_safe(m_ini.group(1))

    # ---------- Tubería de impulsión ----------
    m = re.search(r'tuber[ií]a\s+de\s+impulsi[oó]n[\s\S]{0,100}?(\d+[.,]?\d*)\s*mm', t, re.I)
    if m:
        out["parametros"]["diametro_tuberia_impulsion_mm"] = _to_float_safe(m.group(1))

    # ---------- Caudales ----------
    m = re.search(r'caudal[^.\n]{0,80}?(m[aá]x(?:imo)?|instant[aá]neo)[^.\n]{0,40}?(\d{1,3}(?:[.,]\d+)?)\s*l/?s', t, re.I)
    if m:
        out["parametros"]["caudal_max_instantaneo_l_s"] = _to_float_safe(m.group(2))

    m = re.search(r'caudal[^.\n]{0,80}?m[ií]nimo[^.\n]{0,40}?(\d{1,3}(?:[.,]\d+)?)\s*l/?s', t, re.I)
    if m:
        out["parametros"]["caudal_minimo_l_s"] = _to_float_safe(m.group(1))

    # ---------- Potencia de bombeo ----------
    m_combo = re.search(r'(\d+[.,]?\d*)\s*C\.?\s*V\.?\s*\(\s*(\d+[.,]?\d*)\s*kW\s*\)', t, re.I)
    if m_combo:
        out["parametros"]["potencia_bombeo_kw"] = _to_float_safe(m_combo.group(2))
    else:
        m_kw = re.search(r'\b(\d+[.,]?\d*)\s*kW\b', t, re.I)
        if m_kw:
            out["parametros"]["potencia_bombeo_kw"] = _to_float_safe(m_kw.group(1))
        else:
            m_cv = re.search(r'\b(\d+[.,]?\d*)\s*C\.?\s*V\.?\b', t, re.I)
            if m_cv:
                cv = _to_float_safe(m_cv.group(1))
                if cv is not None:
                    out["parametros"]["potencia_bombeo_kw"] = round(cv * 0.7355, 2)

    return out


# ----------------- Bloque literal (Caudal necesario / Consumo) -----------------
def extract_consumo_block(texto_completo: str) -> Optional[str]:
    """
    Devuelve el texto literal del apartado '3.1. Caudal necesario'
    hasta el siguiente encabezado (3.2., 4., etc.). Case-insensitive.
    Si no lo encuentra, devuelve None.
    """
    if not texto_completo:
        return None

    patron_inicio = re.compile(
        r"^\s*3[.,]\s*1\s*\)?\s*(?:-|\.)?\s*(?:Caudal\s+necesario)\b.*$",
        re.IGNORECASE | re.MULTILINE
    )
    patron_fin = re.compile(
        r"^\s*(?:3[.,]\s*2\b|4[.,]\s*0?\b|[1-9]\s*\))|^\s*\d+\.\s+[A-ZÁÉÍÓÚÑ]",
        re.IGNORECASE | re.MULTILINE
    )

    m = patron_inicio.search(texto_completo)
    if not m:
        return None

    start = m.start()
    fin_match = patron_fin.search(texto_completo, m.end())
    end = fin_match.start() if fin_match else len(texto_completo)

    bloque = texto_completo[start:end].strip()
    bloque = re.sub(r"^\s*\d+\.\s*[A-ZÁÉÍÓÚÑ].*$", "", bloque, flags=re.MULTILINE).strip()
    return bloque or None
