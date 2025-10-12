from typing import Dict, Any, Optional
from docx import Document
from docx.text.paragraph import Paragraph
from docx.oxml import OxmlElement
import regex as re

NBSP = "\u00A0"
ZWSP = "\u200B"
SOFT = "\u00AD"

# =====================
# Utilidades básicas
# =====================

def _clean(s: str) -> str:
    """Limpia caracteres invisibles y no imprimibles."""
    return (s or "").replace(NBSP, " ").replace(ZWSP, "").replace(SOFT, "")

def _chunks(s: str, n: int = 3000):
    """Divide un texto largo en fragmentos pequeños para evitar errores de Word."""
    for i in range(0, len(s), n):
        yield s[i:i + n]

def _para_text(p: Paragraph) -> str:
    """Extrae el texto completo de un párrafo, incluyendo los runs."""
    return "".join(r.text or "" for r in getattr(p, "runs", [])) or (p.text or "")

def _clear_paragraph(p: Paragraph):
    """Vacía un párrafo sin eliminarlo del documento."""
    for r in list(p.runs):
        r.text = ""
    try:
        for child in list(p._p):
            p._p.remove(child)
    except Exception:
        pass

def _insert_after(p: Paragraph, text: str = "") -> Paragraph:
    """Inserta un nuevo párrafo inmediatamente después del actual."""
    new_p = OxmlElement("w:p")
    p._p.addnext(new_p)
    new_para = Paragraph(new_p, p._parent)
    if text:
        for chunk in _chunks(text):
            new_para.add_run(chunk)
    return new_para

# =====================
# Escritura de bloques
# =====================

def _write_with_paragraphs(para: Paragraph, text: str):
    """
    Escribe texto respetando saltos dobles (\n\n) como nuevos párrafos.
    """
    value = _clean(str(text or ""))
    blocks = [b.strip() for b in value.split("\n\n") if b.strip()]

    if not blocks:
        _clear_paragraph(para)
        return

    next_elem = para._p.getnext()
    _clear_paragraph(para)

    # Primer bloque en el párrafo actual
    para.add_run(blocks[0])

    cur = para
    for b in blocks[1:]:
        cur = _insert_after(cur, b)

    if next_elem is not None and cur._p.getnext() != next_elem:
        cur._p.addnext(next_elem)

# =====================
# Iterador de párrafos
# =====================

def _iter_paragraphs(doc: Document):
    """Itera sobre todos los párrafos del documento (texto, tablas, encabezado y pie)."""
    for p in doc.paragraphs:
        yield p
    for t in doc.tables:
        for r in t.rows:
            for c in r.cells:
                for p in c.paragraphs:
                    yield p
    for section in doc.sections:
        for p in section.header.paragraphs:
            yield p
        for t in section.header.tables:
            for r in t.rows:
                for c in r.cells:
                    for p in c.paragraphs:
                        yield p
        for p in section.footer.paragraphs:
            yield p
        for t in section.footer.tables:
            for r in t.rows:
                for c in r.cells:
                    for p in c.paragraphs:
                        yield p

# =====================
# Reemplazo principal
# =====================

def _replace_placeholders(doc: Document, replacements: Dict[str, Any]):
    """
    Reemplaza todos los {{placeholders}}:
    - Si el párrafo contiene SOLO el marcador → se reemplaza entero con saltos de párrafo.
    - Si hay texto antes o después → se reemplaza inline, manteniendo el resto.
    """
    for para in list(_iter_paragraphs(doc)):
        text = _clean(_para_text(para))
        if "{{" not in text:
            continue

        for key, val in (replacements or {}).items():
            pattern = re.compile(r"\{\{\s*" + re.escape(key) + r"\s*\}\}", re.DOTALL)
            match_full = pattern.fullmatch(text.strip())
            if match_full:
                _write_with_paragraphs(para, val)
                break
            elif pattern.search(text):
                new_text = pattern.sub(str(val or ""), text)
                _clear_paragraph(para)
                para.add_run(new_text)
                break

# =====================
# Relleno de tablas
# =====================

def _fill_tables_by_labels(doc: Document, data: Dict[str, Any]):
    """Rellena tablas con formato 'Etiqueta | Valor'."""
    for t in doc.tables:
        for r in t.rows:
            if len(r.cells) < 2:
                continue
            label = _clean(_para_text(r.cells[0])).lower().strip()
            if not label:
                continue
            for k, v in data.items():
                if label == k.lower().strip() and v not in (None, ""):
                    _clear_paragraph(r.cells[1].paragraphs[0])
                    r.cells[1].paragraphs[0].add_run(str(v))
                    break

# =====================
# Función principal
# =====================

def export_docx_from_placeholder_map(
    placeholder_map: Dict[str, Any],
    plantilla_path: str,
    out_path: str,
    *,
    label_values: Optional[Dict[str, Any]] = None
) -> str:
    """
    Aplica todos los placeholders {{clave}} definidos en un JSON
    sobre una plantilla Word (.docx) y exporta el resultado.
    """

    doc = Document(plantilla_path)

    # Crear el diccionario de reemplazos (sin tocar nada de coordenadas)
    replacements = {str(k): str(v or "") for k, v in (placeholder_map or {}).items()}

    _replace_placeholders(doc, replacements)
    _fill_tables_by_labels(doc, label_values or placeholder_map)

    doc.save(out_path)
    return out_path
