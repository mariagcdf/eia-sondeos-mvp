# core/extraccion/pdf_reader.py
from io import BytesIO
from typing import Tuple, List, Dict
import re
import pdfplumber

# Palabras clave para seleccionar páginas "ricas" para IA
KEYWORDS = [
    "Objeto", "Resumen", "Localización", "Situación", "Coordenadas", "UTM", "Geodésicas",
    "Polígono", "Parcela", "Referencia catastral", "Uso previsto", "abastecimiento", "riego",
    "Profundidad", "Longitud", "Caudal", "Instalaciones", "bomba", "perforación", "tubería",
    "filtros", "instalación eléctrica", "características del sondeo", "diámetro", "entubación",
    "impulsión", "C.V.", "kW", "caudal máximo", "máximo instantáneo", "QMi", "Q M i",
    "Qmax", "Q máx", "Caudal necesario", "Geología", "Hidrogeología", "acuífero",
    "Nivel freático", "permeabilidad", "porosidad", "vulnerabilidad", "Alternativas",
    "Justificación", "Valoración", "Comparativa"
]

# Firmas típicas que queremos purgar siempre (dirección, web, títulos corporativos…)
HEADER_FOOTER_PATTERNS = [
    r"ipsaingenieros\.com",  # dominio
    r"Pl\.\s*San\s*Crist[oó]bal\s*n[ºo]\s*6.*Salamanca",  # dirección
    r"SONDEO\s+DE\s+APOYO.*VEGA\s+DE\s+TERA.*ZAMORA",     # título proyecto en mayús (ajústalo si cambia)
]

def _safe_extract_text(page) -> str:
    """Extrae texto con tolerancias; '' si no hay texto."""
    try:
        txt = page.extract_text(x_tolerance=2, y_tolerance=2)
        return txt or ""
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
    """Elimina líneas que casen con patrones de cabecera/pie conocidos."""
    out = []
    for ln in lines:
        L = ln.strip()
        if any(re.search(pat, L, re.IGNORECASE) for pat in HEADER_FOOTER_PATTERNS):
            continue
        out.append(ln)
    return out

def _strip_common_headers_footers(pages_lines: List[List[str]], head_k: int = 5, foot_k: int = 5) -> List[List[str]]:
    """
    Detecta líneas comunes (cabecera/pie) mirando primeras 'head_k' y últimas 'foot_k' líneas de cada página.
    Si una línea aparece en ≥ 40% de las páginas y mide > 6 chars, la elimina en todas.
    """
    from collections import Counter
    firsts: Counter = Counter()
    lasts: Counter = Counter()
    total = len(pages_lines)

    # normalizar líneas y contar
    norm_pages = []
    for lines in pages_lines:
        L = [_norm_line(x) for x in lines]
        norm_pages.append(L)
        # header candidates
        for l in L[:min(head_k, len(L))]:
            if len(l) > 6:
                firsts[l] += 1
        # footer candidates
        for l in L[-min(foot_k, len(L)):] if L else []:
            if len(l) > 6:
                lasts[l] += 1

    # umbral (40%)
    thr = max(2, int(0.4 * total))
    common = set([l for l, c in firsts.items() if c >= thr] + [l for l, c in lasts.items() if c >= thr])

    # aplicar purga de comunes + patrones explícitos
    cleaned_pages = []
    for L in norm_pages:
        # fuera comunes
        L2 = [x for x in L if x not in common]
        # fuera patrones fijos (dominio, dirección…)
        L3 = _purge_explicit_patterns(L2)
        cleaned_pages.append(L3)
    return cleaned_pages

def _page_text_to_lines(txt: str) -> List[str]:
    if not txt:
        return []
    txt = txt.replace("\r", "\n")
    lines = [x for x in txt.split("\n")]
    return lines

def _compose_text_from_lines(lines: List[str]) -> str:
    return "\n".join(lines)

def _read_all_pages(uploaded_file) -> List[str]:
    """Lee todo el PDF y devuelve lista de textos por página (sin post-proceso)."""
    raw = uploaded_file.read()
    uploaded_file.seek(0)
    out: List[str] = []
    with pdfplumber.open(BytesIO(raw)) as pdf:
        for p in pdf.pages:
            out.append(_safe_extract_text(p))
    return out

def _clean_pages_texts(pages_texts: List[str]) -> List[str]:
    """Aplica limpieza: quitar headers/footers comunes y patrones explícitos."""
    pages_lines = [_page_text_to_lines(t) for t in pages_texts]
    pages_lines = _strip_common_headers_footers(pages_lines, head_k=5, foot_k=5)
    # post: compactar espacios y quitar espacios de fin
    cleaned = []
    for L in pages_lines:
        L2 = [re.sub(r"[ \t]+$", "", x) for x in L]
        cleaned.append(L2)
    return [ _compose_text_from_lines(L) for L in cleaned ]

def leer_paginas_relevantes_from_upload(uploaded_file, max_pages: int = 40, max_chars: int = 15000) -> Tuple[str, List[int]]:
    """
    Devuelve texto concatenado de páginas con KEYWORDS + lista de páginas usadas.
    Previo: limpieza de headers/footers para no “colar” direcciones, web, ni títulos fijos.
    """
    pages_texts = _read_all_pages(uploaded_file)
    cleaned_texts = _clean_pages_texts(pages_texts)

    paginas_texto: List[str] = []
    usadas: List[int] = []

    seleccion: List[tuple] = []
    for idx, txt in enumerate(cleaned_texts, start=1):
        if any(kw.lower() in txt.lower() for kw in KEYWORDS):
            seleccion.append((idx, txt))

    if not seleccion:
        # Fallback: primeras max_pages ya limpias
        seleccion = [(i + 1, t) for i, t in enumerate(cleaned_texts[:max_pages])]

    usadas = [i for i, _ in seleccion]
    for i, txt in seleccion:
        paginas_texto.append(f"\n--- Página {i} ---\n{txt}")

    texto = "\n".join(paginas_texto)
    if max_chars and max_chars > 0:
        texto = texto[:max_chars]
    return texto, usadas

def leer_pdf_texto_completo(uploaded_file) -> str:
    """
    Devuelve TODO el texto del PDF (para regex o cortes literales),
    ya sin cabeceras/pies repetidos ni patrones explícitos.
    """
    pages_texts = _read_all_pages(uploaded_file)
    cleaned_texts = _clean_pages_texts(pages_texts)
    textos: List[str] = []
    for i, txt in enumerate(cleaned_texts, start=1):
        textos.append(f"\n--- Página {i} ---\n{txt}")
    return "\n".join(textos)
