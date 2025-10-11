from io import BytesIO
from typing import Tuple, List
import re
import pdfplumber

# Palabras clave para seleccionar páginas "ricas"
KEYWORDS = [
    "Objeto", "Resumen", "Localización", "Situación", "Emplazamiento", "Coordenadas", "UTM", "Geodésicas",
    "Polígono", "Parcela", "Referencia catastral", "Uso previsto", "abastecimiento", "riego",
    "Profundidad", "Longitud", "Caudal", "Instalaciones", "bomba", "perforación", "tubería",
    "filtros", "instalación eléctrica", "características del sondeo", "diámetro", "entubación",
    "impulsión", "C.V.", "kW", "caudal máximo", "máximo instantáneo", "QMi", "Q M i",
    "Qmax", "Q máx", "Caudal necesario", "Geología", "Hidrogeología", "acuífero",
    "Nivel freático", "permeabilidad", "porosidad", "vulnerabilidad", "Alternativas",
    "Justificación", "Valoración", "Comparativa"
]

# Firmas típicas a purgar (cabeceras/pies/leyendas de planos…)
HEADER_FOOTER_PATTERNS = [
    r"ipsaingenieros\.com",
    r"Pl\.\s*San\s*Crist[oó]bal\s*n[ºo]\s*6.*Salamanca",
    r"SONDEO\s+DE\s+APOYO.*VEGA\s+DE\s+TERA.*ZAMORA",
    r"---\s*P[aá]gina\b.+",
    r"^\s*Fdo:\s+.+$",
    r"^\s*Escala\s*:\s*.+$",
    r"^\s*Plano\s+n[uú]mero\s*.+$",
    r"^\s*Fecha\s*:\s*.+$",
    r"^\s*PROYECTO\s+DE\s*:\s*.+$",
    r"^\s*PROMOTORES\s+.+$",
    r"^\s*ÁREA\s+DEL\s+PROYECTO\s*$",
    r"^\s*EMPLAZAMIENTO\s*$",
    r"^\s*Localización\s*[0-9/]*\s*$",
]

def _safe_extract_text(page) -> str:
    try:
        return page.extract_text(x_tolerance=2, y_tolerance=2) or ""
    except Exception:
        try:
            return page.extract_text() or ""
        except Exception:
            return ""

def _norm_line(s: str) -> str:
    s = s.replace("\r", "").replace("\t", " ").strip()
    s = re.sub(r"[ \u00A0]{2,}", " ", s)
    return s

def _purge_explicit_patterns(lines: List[str]) -> List[str]:
    out = []
    for ln in lines:
        L = ln.strip()
        if any(re.search(pat, L, re.IGNORECASE) for pat in HEADER_FOOTER_PATTERNS):
            continue
        out.append(ln)
    return out

def _strip_common_headers_footers(pages_lines: List[List[str]], head_k: int = 5, foot_k: int = 5) -> List[List[str]]:
    from collections import Counter
    firsts, lasts = Counter(), Counter()
    total = len(pages_lines)

    norm_pages = []
    for lines in pages_lines:
        L = [_norm_line(x) for x in lines]
        norm_pages.append(L)
        for l in L[:min(head_k, len(L))]:
            if len(l) > 6: firsts[l] += 1
        for l in L[-min(foot_k, len(L)):] if L else []:
            if len(l) > 6: lasts[l] += 1

    thr = max(2, int(0.4 * total))
    common = set([l for l, c in firsts.items() if c >= thr] + [l for l, c in lasts.items() if c >= thr])

    cleaned_pages = []
    for L in norm_pages:
        L2 = [x for x in L if x not in common]
        L3 = _purge_explicit_patterns(L2)
        cleaned_pages.append(L3)
    return cleaned_pages

def _read_all_pages(uploaded_file) -> List[str]:
    raw = uploaded_file.read()
    uploaded_file.seek(0)
    out: List[str] = []
    with pdfplumber.open(BytesIO(raw)) as pdf:
        for p in pdf.pages:
            out.append(_safe_extract_text(p))
    return out

def _page_text_to_lines(txt: str) -> List[str]:
    if not txt: return []
    return txt.replace("\r", "\n").split("\n")

def _compose_text_from_lines(lines: List[str]) -> str:
    lines = [ln for ln in lines if not re.search(r"---\s*P[aá]gina\b.+", ln, flags=re.IGNORECASE)]
    return "\n".join(lines)

def _clean_pages_texts(pages_texts: List[str]) -> List[str]:
    pages_lines = [_page_text_to_lines(t) for t in pages_texts]
    pages_lines = _strip_common_headers_footers(pages_lines, head_k=5, foot_k=5)
    cleaned = []
    for L in pages_lines:
        L2 = [re.sub(r"[ \t]+$", "", x) for x in L]
        cleaned.append(_compose_text_from_lines(L2))
    return cleaned

def leer_paginas_relevantes_from_upload(uploaded_file, max_pages: int = 40, max_chars: int = 15000) -> Tuple[str, List[int]]:
    pages_texts = _read_all_pages(uploaded_file)
    cleaned_texts = _clean_pages_texts(pages_texts)

    seleccion = []
    for idx, txt in enumerate(cleaned_texts, start=1):
        if any(kw.lower() in txt.lower() for kw in KEYWORDS):
            seleccion.append((idx, txt))
    if not seleccion:
        seleccion = [(i + 1, t) for i, t in enumerate(cleaned_texts[:max_pages])]

    usadas = [i for i, _ in seleccion]
    texto = "\n\n".join(txt for _, txt in seleccion)
    if max_chars and max_chars > 0:
        texto = texto[:max_chars]
    return texto, usadas

def leer_pdf_texto_completo(uploaded_file) -> str:
    pages_texts = _read_all_pages(uploaded_file)
    cleaned_texts = _clean_pages_texts(pages_texts)
    return "\n\n".join(cleaned_texts)
