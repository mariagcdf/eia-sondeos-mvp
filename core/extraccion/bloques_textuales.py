# core/extraccion/bloques_textuales.py
from typing import Dict
import re

NBSP = "\u00A0"
SOFT_HYPHEN = "\u00AD"

def _sanitize_pdf_text(s: str) -> str:
    if not s:
        return ""
    s = s.replace("\r", "\n")
    s = s.replace(NBSP, " ").replace(SOFT_HYPHEN, "")
    # desguionar por salto: "pala-\nbra" -> "palabra"
    s = re.sub(r"(?<=\w)-\n(?=\w)", "", s)
    # compactar espacios
    s = re.sub(r"[ \t]+", " ", s)
    # normalizar saltos
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def _quitar_lineas_indice(t: str) -> str:
    out = []
    for line in t.splitlines():
        L = line.strip()
        if re.search(r"\.{3,}\s*\d{1,4}\s*$", L):
            continue
        if re.search(r"^\s*(Contenido|Índice)\s*:?\s*$", L, re.IGNORECASE):
            continue
        out.append(line)
    return "\n".join(out)

def _cortar_despues_del_indice(t: str) -> str:
    # Corta en la página siguiente a la palabra "Contenido" o "Índice"
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

def _cortar_bloque_flexible(texto: str, start_keys, stop_keys) -> str:
    # Busca el primer start que case; corta hasta el primer stop que aparezca después
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

def extraer_bloques_literal(texto_completo: str) -> Dict[str, str]:
    """
    Devuelve bloques limpios y robustos listos para meter en placeholders.
    Claves: ajusta para que coincidan EXACTAMENTE con tus marcadores (p. ej. 'PH_Antecedentes').
    """
    # 1) Normaliza
    t = _sanitize_pdf_text(texto_completo)
    t = _quitar_lineas_indice(t)

    # 2) Patrones robustos (ancla a inicio de línea, tolera variantes)
    pat_antecedentes = [
        r"(?m)^\s*1[.,]?\s*1\b.*Antecedentes",
        r"(?m)^\s*1[.,]?\s*Introducci[oó]n\b",
        r"(?m)^\s*Cap[ií]tulo\s*1\b.*Introducci[oó]n",
    ]
    stop_antecedentes = [
        r"(?m)^\s*1[.,]?\s*2\b",
        r"(?m)^\s*Objeto\b",
        r"(?m)^\s*2[.,]?\s*0?\b",
        r"(?m)^\s*GEOLOG[ÍI]A\b",
        r"(?m)^\s*Geolog[ií]a\b",
        r"(?m)^\s*Situaci[oó]n\b",
        r"(?m)^\s*Emplazamiento\b",
    ]

    pat_situacion = [
        r"(?m)^\s*2[.,]?\s*1\b.*Situaci[oó]n",
        r"(?m)^\s*Situaci[oó]n\b",
        r"(?m)^\s*Emplazamiento\b",
    ]
    stop_situacion = [
        r"(?m)^\s*2[.,]?\s*2\b",
        r"(?m)^\s*Descripci[oó]n\b",
        r"(?m)^\s*3[.,]?\s*\b",
        r"(?m)^\s*GEOLOG",
    ]

    # --- CARACTERÍSTICAS DEL SONDEO (solo 3.1 Caudal necesario) ---
    pat_consumo = [
        r"(?m)^\s*3[.,]?\s*CARACTER[ÍI]STICAS\s+DEL\s+SONDEO\b",
        r"(?m)^\s*CARACTER[ÍI]STICAS\s+DEL\s+SONDEO\b",
    ]

    # cortamos cuando empiece 3.2, o el siguiente capítulo (4., 5., etc.)
    stop_consumo = [
        r"(?m)^\s*3[.,]?\s*2\b",          # secciones siguientes como 3.2, 3.3...
        r"(?m)^\s*4[.,]?\s*\b",           # siguiente capítulo principal
        r"(?m)^\s*REALIZACI[ÓO]N\b",
        r"(?m)^\s*Instalaci[oó]n",
        r"(?m)^\s*SONDEO\s+PARA",         # a veces el título siguiente se imprime en mayúsculas
    ]


    pat_geologia = [
        r"(?m)^\s*GEOLOG[ÍI]A\s*E?\s*HIDROGEOLOG[ÍI]A\b",
        r"(?m)^\s*Geolog[ií]a\b",
    ]
    stop_geologia = [
        r"(?m)^\s*3[.,]?\s*\b",
        r"(?m)^\s*CARACTER[ÍI]STICAS\b",
        r"(?m)^\s*REALIZACI[ÓO]N\b",
        r"(?m)^\s*4[.,]?\s*\b",
        r"(?m)^\s*Valores\s+ambientales\b",
    ]

    antecedentes = _cortar_bloque_flexible(t, pat_antecedentes, stop_antecedentes)
    if len(antecedentes) < 400:
        # Reintento tras cortar el índice
        t2 = _cortar_despues_del_indice(t)
        antecedentes = _cortar_bloque_flexible(t2, pat_antecedentes, stop_antecedentes)

    bloques = {
        # ⚠️ Ajusta las claves a tus placeholders EXACTOS
        "PH_Antecedentes": antecedentes,
        "PH_Situacion": _cortar_bloque_flexible(t, pat_situacion, stop_situacion),
        "PH_Consumo": _cortar_bloque_flexible(t, pat_consumo, stop_consumo),
        "PH_Geologia": _cortar_bloque_flexible(t, pat_geologia, stop_geologia),
    }

    # Limpieza final tipo HTML -> texto
    out = {}
    for k, v in bloques.items():
        v2 = (v or "").replace("<br />", "\n").replace("<br/>", "\n").replace("<br>", "\n").strip()
        out[k] = v2
    return out
