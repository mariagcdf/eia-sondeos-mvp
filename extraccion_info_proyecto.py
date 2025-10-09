# extraccion_info_proyecto.py
# 1) Construye un JSON placeholder->valor a partir del PDF + plantilla
# 2) Inyecta ese JSON en la plantilla y genera el DOCX
# Sin bridges: se rellena SOLO lo que exista en la plantilla.

from typing import Tuple, List, Dict, Any, Optional
from dotenv import load_dotenv
import json
import os

# Ajusta estos imports a tu proyecto:
from core import regex_extract, render_html
from core.extraccion.pdf_reader import (
    leer_paginas_relevantes_from_upload,
    leer_pdf_texto_completo
)
from core.extraccion.bloques_textuales import extraer_bloques_literal
from core.export_docx_template import export_docx_from_placeholder_map

from docx import Document
import re

load_dotenv(override=True)


# ----------------------------
# Utilidades locales
# ----------------------------

def _collect_placeholders_in_doc(doc: Document) -> Dict[str, int]:
    """Devuelve {placeholder: cuenta} encontrados en cuerpo, tablas, encabezados y pies."""
    found = {}

    def harvest(txt: str):
        for m in re.finditer(r"\{\{([^{}]+)\}\}", txt or ""):
            key = (m.group(1) or "").strip()
            if key:
                found[key] = found.get(key, 0) + 1

    # cuerpo
    for p in doc.paragraphs:
        if "{{" in p.text:
            harvest("".join(r.text for r in p.runs) or p.text)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    if "{{" in para.text:
                        harvest("".join(r.text for r in para.runs) or para.text)

    # headers / footers
    for section in doc.sections:
        # header
        for para in section.header.paragraphs:
            if "{{" in para.text:
                harvest("".join(r.text for r in para.runs) or para.text)
        for table in section.header.tables:
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        if "{{" in para.text:
                            harvest("".join(r.text for r in para.runs) or para.text)
        # footer
        for para in section.footer.paragraphs:
            if "{{" in para.text:
                harvest("".join(r.text for r in para.runs) or para.text)
        for table in section.footer.tables:
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        if "{{" in para.text:
                            harvest("".join(r.text for r in para.runs) or para.text)
    return found


def _table_from_coords(coords: Dict[str, Any]) -> str:
    if not coords:
        return "—"
    utm = (coords.get("utm") or {})
    x = utm.get("x", "—"); y = utm.get("y", "—")
    huso = utm.get("huso", "—"); datum = utm.get("datum", "—")
    return f"UTM X: {x}\nUTM Y: {y}\nHuso: {huso}\nDatum: {datum}"


# ----------------------------
# 1) Extracción
# ----------------------------

def extract_from_project_and_eia(
    uploaded_file,
    eia_docx: Optional[str] = None,
    model: str = "gpt-4.1-mini",   # <--- añadido para compatibilidad
    max_pages: int = 40,
    max_chars: int = 15000
) -> Tuple[Dict[str, Any], List[int], str]:
    """
    Devuelve:
      - datos_regex: dict con parámetros/localización/coordenadas (regex)
      - usadas: páginas usadas (solo informativo)
      - html: vista previa (si tienes renderizador)
    """
    texto_relevante, usadas = leer_paginas_relevantes_from_upload(
        uploaded_file, max_pages=max_pages, max_chars=max_chars
    )
    texto_completo = leer_pdf_texto_completo(uploaded_file)

    datos_regex = regex_extract.regex_extract_min_fields(texto_completo)

    literal_blocks = extraer_bloques_literal(texto_completo)
    try:
        literal_blocks.setdefault("PH_Consumo", regex_extract.extract_consumo_block(texto_completo) or "")
    except Exception:
        pass

    try:
        html = render_html.render_html(datos_regex, literal_blocks)
    except Exception:
        html = "<p>Vista previa no disponible.</p>"


    return datos_regex, usadas, html


# ----------------------------
# 2) Construcción del JSON de placeholders (antes de exportar)
# ----------------------------

def build_placeholder_json_for_template(
    plantilla_path: str,
    datos_min: Dict[str, Any],
    literal_blocks: Dict[str, str],
    save_to: Optional[str] = None
) -> Dict[str, str]:
    """
    Lee la plantilla, detecta qué placeholders hay y construye un JSON
    con los valores que vamos a inyectar:
      1) literal_blocks[<placeholder exacto>] (bloques largos aquí)
      2) datos_min['parametros'][<placeholder>]
      3) datos_min['localizacion'][<placeholder>]
      4) datos_min[<placeholder>]
      5) 'tabla_coordenadas' -> formato útil
      6) resto -> ""
    """
    doc = Document(plantilla_path)
    phs = _collect_placeholders_in_doc(doc)

    p = (datos_min.get("parametros") or {})
    loc = (datos_min.get("localizacion") or {})
    coords = (datos_min.get("coordenadas") or {})
    lb = literal_blocks or {}

    def value_for(ph: str):
        if ph in lb and isinstance(lb[ph], (str, int, float)):
            return lb[ph]
        if ph in (p or {}):
            return p.get(ph, "")
        if ph in (loc or {}):
            return loc.get(ph, "")
        if ph in (datos_min or {}):
            return datos_min.get(ph, "")
        if ph == "tabla_coordenadas":
            return _table_from_coords(coords)
        return ""

    placeholder_map: Dict[str, str] = {}
    for ph in phs.keys():
        val = value_for(ph)
        if isinstance(val, (str, int, float)):
            placeholder_map[ph] = str(val)

    if save_to:
        try:
            with open(save_to, "w", encoding="utf-8") as f:
                json.dump(placeholder_map, f, ensure_ascii=False, indent=2)
            print(f"💾 JSON de placeholders guardado en: {os.path.basename(save_to)}")
        except Exception as e:
            print("⚠️ No se pudo guardar el JSON de placeholders:", e)

    return placeholder_map


# ----------------------------
# 3) Exportador: usa el JSON ya construido
# ----------------------------

def export_eia_docx(
    datos_min: Dict[str, Any],
    literal_blocks: Dict[str, str],
    out_path: str,
    plantilla_path: str = "plantilla_EIA.docx",
    save_json_al_lado: bool = True
) -> str:
    """
    - Construye el JSON de placeholders según la plantilla
    - Exporta inyectando ese JSON (soporta textos largos)
    """
    json_path = None
    if save_json_al_lado:
        out_dir = os.path.join(os.getcwd(), "resultados_pruebas")
        os.makedirs(out_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(out_path))[0]
        json_path = os.path.join(out_dir, f"{base_name}.placeholders.json")


    placeholder_map = build_placeholder_json_for_template(
        plantilla_path=plantilla_path,
        datos_min=datos_min,
        literal_blocks=literal_blocks,
        save_to=json_path
    )

    return export_docx_from_placeholder_map(
        placeholder_map=placeholder_map,
        plantilla_path=plantilla_path,
        out_path=out_path
    )
