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
    "Nivel freático", "permeabilidad", "porosidad", "vulnerabilidad"
]

def leer_paginas_relevantes_from_upload(uploaded_file, max_pages: int = 40, max_chars: int = 15000) -> Tuple[str, List[int]]:
    """Devuelve texto concatenado de páginas con KEYWORDS (para IA) + lista de páginas usadas."""
    raw = uploaded_file.read()
    uploaded_file.seek(0)

    paginas_texto = []
    usadas: List[int] = []
    with pdfplumber.open(BytesIO(raw)) as pdf:
        seleccion: List[tuple] = []
        for idx, page in enumerate(pdf.pages, start=1):
            txt = page.extract_text() or ""
            if any(kw.lower() in txt.lower() for kw in KEYWORDS):
                seleccion.append((idx, txt))
        if not seleccion:
            seleccion = [(i + 1, p.extract_text() or "") for i, p in enumerate(pdf.pages[:max_pages])]
        usadas = [i for i, _ in seleccion]
        for i, txt in seleccion:
            paginas_texto.append(f"\n--- Página {i} ---\n{txt}")

    texto = "\n".join(paginas_texto)[:max_chars]
    return texto, usadas


def leer_pdf_texto_completo(uploaded_file) -> str:
    """Devuelve TODO el texto del PDF (para regex o cortes literales)."""
    raw = uploaded_file.read()
    uploaded_file.seek(0)
    textos = []
    with pdfplumber.open(BytesIO(raw)) as pdf:
        for i, p in enumerate(pdf.pages, start=1):
            txt = p.extract_text() or ""
            textos.append(f"\n--- Página {i} ---\n{txt}")
    return "\n".join(textos)
