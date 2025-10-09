# core/extraccion/pdf_reader.py
from io import BytesIO
from typing import Tuple, List
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

def _safe_extract_text(page) -> str:
    """
    Extrae texto con cierta tolerancia para mejorar unión de palabras/columnas.
    Devuelve "" si no hay texto (p.ej. PDF escaneado).
    """
    try:
        txt = page.extract_text(x_tolerance=2, y_tolerance=2)
        return txt or ""
    except Exception:
        try:
            return page.extract_text() or ""
        except Exception:
            return ""

def leer_paginas_relevantes_from_upload(uploaded_file, max_pages: int = 40, max_chars: int = 15000) -> Tuple[str, List[int]]:
    """Devuelve texto concatenado de páginas con KEYWORDS (para IA) + lista de páginas usadas."""
    raw = uploaded_file.read()
    uploaded_file.seek(0)

    paginas_texto: List[str] = []
    usadas: List[int] = []

    with pdfplumber.open(BytesIO(raw)) as pdf:
        seleccion: List[tuple] = []
        for idx, page in enumerate(pdf.pages, start=1):
            txt = _safe_extract_text(page)
            if any(kw.lower() in txt.lower() for kw in KEYWORDS):
                seleccion.append((idx, txt))

        if not seleccion:
            # Fallback: primeras max_pages
            seleccion = [(i + 1, _safe_extract_text(p)) for i, p in enumerate(pdf.pages[:max_pages])]

        usadas = [i for i, _ in seleccion]
        for i, txt in seleccion:
            paginas_texto.append(f"\n--- Página {i} ---\n{txt}")

    texto = "\n".join(paginas_texto)
    if max_chars and max_chars > 0:
        texto = texto[:max_chars]
    return texto, usadas

def leer_pdf_texto_completo(uploaded_file) -> str:
    """Devuelve TODO el texto del PDF (para regex o cortes literales)."""
    raw = uploaded_file.read()
    uploaded_file.seek(0)
    textos: List[str] = []
    with pdfplumber.open(BytesIO(raw)) as pdf:
        for i, p in enumerate(pdf.pages, start=1):
            txt = _safe_extract_text(p)
            textos.append(f"\n--- Página {i} ---\n{txt}")
    return "\n".join(textos)
