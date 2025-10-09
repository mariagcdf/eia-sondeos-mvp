# core/export_docx_template.py
# Recibe un JSON (placeholder -> valor) y lo vuelca en el DOCX
# con soporte de textos largos, párrafos reales y listas.

from typing import Dict, Any
import re
from docx import Document
from docx.text.paragraph import Paragraph
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

# =========================
# Utilidades de texto
# =========================

def _norm_block_text(s: str) -> str:
    """Normaliza un bloque de texto antes de volcarlo a DOCX."""
    if s is None:
        return ""
    # Normalizar finales de línea
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    # Quitar espacios a final de línea
    s = re.sub(r"[ \t]+\n", "\n", s)
    # Compactar espacios múltiples
    s = re.sub(r"[ \t]{2,}", " ", s)
    # Compactar saltos: como mucho dos seguidos
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()

def _is_bullet_line(line: str) -> bool:
    """Detecta una línea de lista con viñeta simple."""
    return bool(re.match(r"^\s*(?:[-*•–])\s+\S", line))

def _split_blocks_by_blanklines(text: str):
    """Divide por párrafos a partir de líneas en blanco (doble salto)."""
    # Bloques separados por líneas en blanco
    return [b for b in re.split(r"\n\s*\n", text) if b.strip()]

def _split_lines(text: str):
    """Divide en líneas preservando saltos simples."""
    return text.split("\n")

# =========================
# Bajo nivel: insertar párrafo tras otro (Oxml)
# =========================

def _insert_paragraph_after(paragraph: Paragraph) -> Paragraph:
    """
    Inserta y devuelve un párrafo justo después del dado (bajo nivel).
    Preserva el mismo contenedor y permite aplicar estilos después.
    """
    p = paragraph._p
    new_p = OxmlElement("w:p")
    p.addnext(new_p)
    return Paragraph(new_p, paragraph._parent)

# =========================
# Motor de escritura
# =========================

def _clear_paragraph(para: Paragraph):
    # Borra todos los runs del párrafo (contenido)
    for r in para.runs:
        r.text = ""
    # Elimina elementos de los runs para dejarlo vacío
    while para.runs:
        para.runs[0]._element.getparent().remove(para.runs[0]._element)

def _append_text_with_linebreaks(para: Paragraph, text: str):
    """
    Añade texto dentro de un mismo párrafo:
    - '\n' -> salto de línea (w:br)
    (NO crea nuevos párrafos)
    """
    parts = text.split("\n")
    for i, part in enumerate(parts):
        if part:
            para.add_run(part)
        if i < len(parts) - 1:
            br = para.add_run()
            br.add_break()

def _apply_bullet_style_if_available(para: Paragraph):
    """
    Intenta aplicar 'List Bullet' si existe; si no, deja el estilo tal cual.
    """
    try:
        para.style = para.part.document.styles["List Bullet"]
    except Exception:
        # Si no existe el estilo, lo dejamos con el estilo heredado
        pass

def _expand_block_into_paragraphs(para: Paragraph, raw_text: str):
    """
    Expande un bloque grande sobre un placeholder que ocupa todo el párrafo.
    - Respeta el estilo base del párrafo.
    - Crea nuevos párrafos (doble salto).
    - Soporta listas simples (viñetas).
    """
    base_style = para.style
    text = _norm_block_text(raw_text)

    # Si viene vacío, borra el párrafo y listo
    _clear_paragraph(para)
    if not text:
        return

    blocks = _split_blocks_by_blanklines(text)

    def add_block_as_paragraphs(block_text: str, first_target_para: Paragraph):
        """
        Vuelca un bloque. Si detecta viñetas en (casi) todas las líneas,
        genera un párrafo por línea con estilo de lista.
        Si no, vuelca el bloque como texto con saltos de línea dentro de un párrafo.
        """
        lines = _split_lines(block_text)
        # Heurística: ¿es lista? (≥ 2 líneas y mayoría con marca)
        bullet_count = sum(1 for ln in lines if _is_bullet_line(ln))
        is_list = len(lines) >= 2 and bullet_count >= max(2, int(0.6 * len(lines)))

        cur = first_target_para
        cur.style = base_style  # conservar estilo base

        if is_list:
            # Cada línea -> párrafo con estilo de lista
            # Primero, si la primera línea era para el párrafo inicial, lo reutilizamos;
            # si no, insertamos después.
            # Limpiamos el párrafo por si acaso
            _clear_paragraph(cur)
            wrote_first = False
            for ln in lines:
                # Limpia el prefijo de viñeta antes de añadir el texto
                clean = re.sub(r"^\s*(?:[-*•–])\s+", "", ln).strip()
                if not wrote_first:
                    cur.add_run(clean)
                    _apply_bullet_style_if_available(cur)
                    wrote_first = True
                else:
                    np = _insert_paragraph_after(cur)
                    np.style = base_style
                    np.add_run(clean)
                    _apply_bullet_style_if_available(np)
                    cur = np
        else:
            # Mismo párrafo con saltos de línea
            _clear_paragraph(cur)
            _append_text_with_linebreaks(cur, block_text)
        return cur

    # Primer bloque en el párrafo original
    cur = add_block_as_paragraphs(blocks[0], para)

    # Resto de bloques, cada uno empieza en párrafo nuevo
    for b in blocks[1:]:
        np = _insert_paragraph_after(cur)
        np.style = base_style
        cur = add_block_as_paragraphs(b, np)

def _replace_placeholder_block_in_paragraph(para: Paragraph, placeholder: str, value: str) -> bool:
    """
    Si el párrafo contiene {{placeholder}}:
      - Si el placeholder ocupa TODO el párrafo => expansión bonita (párrafos reales).
      - Si es inline => reemplazo dentro del mismo párrafo, preservando el resto.
    Devuelve True si reemplazó.
    """
    token = f"{{{{{placeholder}}}}}"
    # Unir runs para localizar el token con fiabilidad
    full_text = "".join(r.text for r in para.runs) if para.runs else para.text

    if token not in full_text:
        return False

    # ¿Ocupa todo el párrafo (ignorando espacios)?
    if full_text.strip() == token:
        _expand_block_into_paragraphs(para, value or "")
        return True

    # Reemplazo inline simple (no crea nuevos párrafos)
    new_text = full_text.replace(token, "" if value is None else str(value))
    _clear_paragraph(para)
    _append_text_with_linebreaks(para, new_text)
    return True

def _replace_placeholder_block_everywhere(doc: Document, replacements: Dict[str, str]):
    """
    Reemplaza en cuerpo, tablas, encabezados y pies.
    Usa el motor de bloque largo que crea párrafos/saltos si procede.
    """
    # Cuerpo
    for para in doc.paragraphs:
        if "{{" in para.text:
            for k, v in replacements.items():
                _replace_placeholder_block_in_paragraph(para, k, v)

    # Tablas
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    if "{{" in para.text:
                        for k, v in replacements.items():
                            _replace_placeholder_block_in_paragraph(para, k, v)

    # Encabezados / Pies
    for section in doc.sections:
        # Header
        for para in section.header.paragraphs:
            if "{{" in para.text:
                for k, v in replacements.items():
                    _replace_placeholder_block_in_paragraph(para, k, v)
        for table in section.header.tables:
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        if "{{" in para.text:
                            for k, v in replacements.items():
                                _replace_placeholder_block_in_paragraph(para, k, v)
        # Footer
        for para in section.footer.paragraphs:
            if "{{" in para.text:
                for k, v in replacements.items():
                    _replace_placeholder_block_in_paragraph(para, k, v)
        for table in section.footer.tables:
            for row in table.rows:
                for cell in row.cells:
                    for para in cell.paragraphs:
                        if "{{" in para.text:
                            for k, v in replacements.items():
                                _replace_placeholder_block_in_paragraph(para, k, v)

# =========================
# Exportador simple (sin bridges)
# =========================

def export_docx_from_placeholder_map(
    placeholder_map: Dict[str, str],
    plantilla_path: str,
    out_path: str
) -> str:
    """
    Recibe el JSON {placeholder: valor} y lo inyecta en la plantilla.
    Soporta textos largos (crea párrafos y saltos) y listas.
    """
    doc = Document(plantilla_path)

    # Solo strings en el mapa final + normalización mínima
    def _to_str(v):
        if v is None:
            return ""
        if isinstance(v, (int, float)):
            return str(v)
        return str(v)

    replacements = {k: _norm_block_text(_to_str(v)) for k, v in (placeholder_map or {}).items()}

    _replace_placeholder_block_everywhere(doc, replacements)
    doc.save(out_path)
    return out_path
