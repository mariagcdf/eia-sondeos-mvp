# core/extraccion/bloques_textuales.py
from typing import Dict, List
import re

NBSP = "\u00A0"
SOFT_HYPHEN = "\u00AD"

# =========================
# Utilidades de normalización
# =========================
def _sanitize_pdf_text(s: str) -> str:
    if not s:
        return ""
    s = s.replace("\r", "\n")
    s = s.replace(NBSP, " ").replace(SOFT_HYPHEN, "")
    # desguionar por salto: "pala-\nbra" -> "palabra"
    s = re.sub(r"(?<=\w)-\n(?=\w)", "", s)
    # compactar espacios
    s = re.sub(r"[ \t]+", " ", s)
    # normalizar saltos múltiples
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def _quitar_lineas_indice(t: str) -> str:
    out = []
    for line in t.splitlines():
        L = line.strip()
        # líneas tipo índice con puntos y número al final
        if re.search(r"\.{3,}\s*\d{1,4}\s*$", L):
            continue
        if re.search(r"^\s*(Contenido|Índice)\s*:?\s*$", L, re.IGNORECASE):
            continue
        out.append(line)
    return "\n".join(out)

def _cortar_despues_del_indice(t: str) -> str:
    # Corta en la página siguiente a "Contenido" o "Índice" si el PDF trae un índice largo al principio
    pag_marks = [m.start() for m in re.finditer(r"--- Página \d+ ---", t)]
    pag_marks.append(len(t))
    m = re.search(r"(?im)^\s*(Contenido|Índice)\s*$", t)
    if not m:
        return t
    idx_page = None
    for i in range(len(pag_marks)-1):
        if pag_marks[i] <= m.start() < pag_marks[i+1]:
            idx_page = i
            break
    if idx_page is None:
        return t
    cut_pos = pag_marks[idx_page+1]
    return t[cut_pos:]

# =========================
# Cortador flexible de bloques
# =========================
def _cortar_bloque_flexible(texto: str, start_keys: List[str], stop_keys: List[str]) -> str:
    """
    Busca el primer patrón de inicio que case; corta hasta el primer patrón de parada posterior.
    """
    start_match = None
    for s in start_keys:
        m = re.search(s, texto, flags=re.IGNORECASE | re.MULTILINE)
        if m:
            start_match = m
            break
    if not start_match:
        return ""
    start = start_match.start()

    stop = len(texto)
    for e in stop_keys:
        m2 = re.search(e, texto[start:], flags=re.IGNORECASE | re.MULTILINE)
        if m2:
            stop = start + m2.start()
            break

    return texto[start:stop].strip()

# =========================
# Extractores de campos cortos (municipio, provincia)
# =========================
def _buscar_primera_captura(texto: str, patrones: List[str], flags=re.IGNORECASE | re.MULTILINE) -> str:
    for pat in patrones:
        m = re.search(pat, texto, flags=flags)
        if m:
            # Devuelve el primer grupo con contenido significativo
            for g in range(1, (m.lastindex or 0) + 1):
                val = (m.group(g) or "").strip(" :-\t\n\r")
                if val:
                    # Limpiar puntos finales y espacios dobles
                    val = re.sub(r"[ \t]{2,}", " ", val).strip(" .")
                    return val
    return ""

def _extraer_municipio(texto: str) -> str:
    patrones = [
        r"(?i)\bMunicipio\s*:\s*([A-Za-zÁÉÍÓÚÜÑáéíóúüñ \-\/]+)",
        r"(?i)\bT[eé]rmino\s+municipal\s*:\s*([A-Za-zÁÉÍÓÚÜÑáéíóúüñ \-\/]+)",
        r"(?i)\bMunicipio\s+de\s+([A-Za-zÁÉÍÓÚÜÑáéíóúüñ \-\/]+)",
        r"(?i)\ben el municipio de\s+([A-Za-zÁÉÍÓÚÜÑáéíóúüñ \-\/]+)",
    ]
    return _buscar_primera_captura(texto, patrones)

def _extraer_provincia(texto: str) -> str:
    patrones = [
        r"(?i)\bProvincia\s*:\s*([A-Za-zÁÉÍÓÚÜÑáéíóúüñ \-\/]+)",
        r"(?i)\bProvincia\s+de\s+([A-Za-zÁÉÍÓÚÜÑáéíóúüñ \-\/]+)",
        r"(?i)\ben la provincia de\s+([A-Za-zÁÉÍÓÚÜÑáéíóúüñ \-\/]+)",
    ]
    return _buscar_primera_captura(texto, patrones)

# =========================
# Función principal de extracción
# =========================
def extraer_bloques_literal(texto_completo: str) -> Dict[str, str]:
    """
    Devuelve un dict listo para inyectar en placeholders del DOCX.
    Las CLAVES devueltas coinciden EXACTAMENTE con tu plantilla/JSON:

      - PH_Antecedentes
      - PH_situacion
      - PH_Consumo
      - alternativas_desc
      - alternativas_val
      - alternativas_just
      - geología
      - municipio
      - provincia

    Si algún bloque no se encuentra, devuelve "" (vacío).
    """
    # 1) Normalizar y limpiar índice
    t = _sanitize_pdf_text(texto_completo or "")
    t = _quitar_lineas_indice(t)

    # ========== PATRONES DE BLOQUES ==========
    # ANTECEDENTES / INTRODUCCIÓN
    pat_antecedentes = [
        r"(?m)^\s*1[.,]?\s*1\b.*Antecedentes",
        r"(?m)^\s*1[.,]?\s*Introducci[oó]n\b",
        r"(?m)^\s*Cap[ií]tulo\s*1\b.*Introducci[oó]n",
        r"(?m)^\s*Antecedentes\b",
    ]
    stop_antecedentes = [
        r"(?m)^\s*1[.,]?\s*2\b",
        r"(?m)^\s*Objeto\b",
        r"(?m)^\s*2[.,]?\s*0?\b",
        r"(?m)^\s*GEOLOG[ÍI]A\b",
        r"(?m)^\s*Geolog[ií]a\b",
        r"(?m)^\s*Situaci[oó]n\b",
        r"(?m)^\s*Emplazamiento\b",
        r"(?m)^\s*Ubicaci[oó]n\b",
        r"(?m)^\s*Localizaci[oó]n\b",
    ]

    # SITUACIÓN / UBICACIÓN / EMPLAZAMIENTO
    pat_situacion = [
        r"(?m)^\s*2[.,]?\s*1\b.*Situaci[oó]n",
        r"(?m)^\s*Situaci[oó]n\b",
        r"(?m)^\s*Emplazamiento\b",
        r"(?m)^\s*Ubicaci[oó]n\b",
        r"(?m)^\s*Localizaci[oó]n\b",
    ]
    stop_situacion = [
        r"(?m)^\s*2[.,]?\s*2\b",
        r"(?m)^\s*Descripci[oó]n\b",
        r"(?m)^\s*3[.,]?\s*\b",
        r"(?m)^\s*GEOLOG",
        r"(?m)^\s*Geolog[ií]a\b",
        r"(?m)^\s*Valores\s+ambientales\b",
    ]

    # CONSUMO / CAUDAL NECESARIO (dentro de CARACTERÍSTICAS DEL SONDEO)
    pat_consumo = [
        r"(?m)^\s*3[.,]?\s*1\b.*(Consumo|Caudal\s+necesario|Demanda)\b",
        r"(?m)^\s*(Consumo|Caudal\s+necesario|Demanda)\b",
        r"(?m)^\s*3[.,]?\s*CARACTER[ÍI]STICAS\s+DEL\s+SONDEO\b",
        r"(?m)^\s*CARACTER[ÍI]STICAS\s+DEL\s+SONDEO\b",
    ]
    stop_consumo = [
        r"(?m)^\s*3[.,]?\s*2\b",          # 3.2, 3.3...
        r"(?m)^\s*4[.,]?\s*\b",           # capítulo 4
        r"(?m)^\s*REALIZACI[ÓO]N\b",
        r"(?m)^\s*Instalaci[oó]n",
        r"(?m)^\s*SONDEO\s+PARA",
        r"(?m)^\s*CARACTER[ÍI]STICAS\s+DE(L|LA)\b.*\n",  # otro título 3.x
    ]

    # GEOLOGÍA / HIDROGEOLOGÍA
    pat_geologia = [
        r"(?m)^\s*GEOLOG[ÍI]A\s*E?\s*HIDROGEOLOG[ÍI]A\b",
        r"(?m)^\s*Geolog[ií]a\b",
        r"(?m)^\s*Hidrogeolog[ií]a\b",
    ]
    stop_geologia = [
        r"(?m)^\s*3[.,]?\s*\b",
        r"(?m)^\s*CARACTER[ÍI]STICAS\b",
        r"(?m)^\s*REALIZACI[ÓO]N\b",
        r"(?m)^\s*4[.,]?\s*\b",
        r"(?m)^\s*Valores\s+ambientales\b",
    ]

    # ALTERNATIVAS (Descripción/Valoración/Justificación)
    pat_alt_desc = [
        r"(?m)^\s*\d+[.,]?\s*\d*\s*Descripci[oó]n\s+de\s+alternativas\b",
        r"(?m)^\s*Alternativas\s*-\s*Descripci[oó]n\b",
        r"(?m)^\s*Descripci[oó]n\s+de\s+Alternativas\b",
        r"(?m)^\s*Alternativas\b",
    ]
    stop_alt_desc = [
        r"(?m)^\s*\d+[.,]?\s*\d*\s*Valoraci[oó]n\b",
        r"(?m)^\s*\d+[.,]?\s*\d*\s*Justificaci[oó]n\b",
        r"(?m)^\s*Valoraci[oó]n\s+de\s+Alternativas\b",
        r"(?m)^\s*Justificaci[oó]n\s+de\s+la\s+alternativa\b",
        r"(?m)^\s*[A-ZÁÉÍÓÚÜÑ][A-Za-zÁÉÍÓÚÜÑ ]{2,}\n",  # siguiente título en capitalizada
    ]

    pat_alt_val = [
        r"(?m)^\s*\d+[.,]?\s*\d*\s*Valoraci[oó]n\s+de\s+alternativas\b",
        r"(?m)^\s*Alternativas\s*-\s*Valoraci[oó]n\b",
        r"(?m)^\s*Valoraci[oó]n\s+de\s+Alternativas\b",
        r"(?m)^\s*Comparativa\s+de\s+alternativas\b",
        r"(?m)^\s*Selecci[oó]n\s+de\s+alternativa\b",
    ]
    stop_alt_val = [
        r"(?m)^\s*\d+[.,]?\s*\d*\s*Justificaci[oó]n\b",
        r"(?m)^\s*Justificaci[oó]n\s+de\s+la\s+alternativa\b",
        r"(?m)^\s*[A-ZÁÉÍÓÚÜÑ][A-Za-zÁÉÍÓÚÜÑ ]{2,}\n",
    ]

    pat_alt_just = [
        r"(?m)^\s*\d+[.,]?\s*\d*\s*Justificaci[oó]n\s+de\s+la\s+alternativa\b",
        r"(?m)^\s*Alternativas\s*-\s*Justificaci[oó]n\b",
        r"(?m)^\s*Justificaci[oó]n\s+de\s+Alternativas\b",
        r"(?m)^\s*Justificaci[oó]n\s+de\s+la\s+alternativa\s+seleccionada\b",
    ]
    stop_alt_just = [
        r"(?m)^\s*[A-ZÁÉÍÓÚÜÑ][A-Za-zÁÉÍÓÚÜÑ ]{2,}\n",
        r"(?m)^\s*\d+[.,]?\s*\d*\s*[A-ZÁÉÍÓÚÜÑ][^\n]{2,}\n",  # siguiente sección numerada
    ]

    # 2) Cortes de bloques
    antecedentes = _cortar_bloque_flexible(t, pat_antecedentes, stop_antecedentes)
    if len(antecedentes) < 400:
        # Reintento tras cortar el índice si quedó corto
        t2 = _cortar_despues_del_indice(t)
        antecedentes = _cortar_bloque_flexible(t2, pat_antecedentes, stop_antecedentes)

    situacion = _cortar_bloque_flexible(t, pat_situacion, stop_situacion)
    consumo = _cortar_bloque_flexible(t, pat_consumo, stop_consumo)
    geologia = _cortar_bloque_flexible(t, pat_geologia, stop_geologia)

    alt_desc = _cortar_bloque_flexible(t, pat_alt_desc, stop_alt_desc)
    alt_val  = _cortar_bloque_flexible(t, pat_alt_val , stop_alt_val )
    alt_just = _cortar_bloque_flexible(t, pat_alt_just, stop_alt_just)

    # 3) Campos cortos (municipio/provincia)
    municipio = _extraer_municipio(t)
    provincia = _extraer_provincia(t)

    # 4) Limpieza final de posibles etiquetas HTML sueltas
    def _clean_htmlish(s: str) -> str:
        return (s or "").replace("<br />", "\n").replace("<br/>", "\n").replace("<br>", "\n").strip()

    bloques = {
        # ⚠️ Claves EXACTAS pedidas por tu plantilla/JSON
        "PH_Antecedentes": _clean_htmlish(antecedentes),
        "PH_situacion":    _clean_htmlish(situacion),
        "PH_Consumo":      _clean_htmlish(consumo),
        "alternativas_desc": _clean_htmlish(alt_desc),
        "alternativas_val":  _clean_htmlish(alt_val),
        "alternativas_just": _clean_htmlish(alt_just),
        "geología":        _clean_htmlish(geologia),
        "municipio":       municipio or "",
        "provincia":       provincia or "",
    }

    return bloques
