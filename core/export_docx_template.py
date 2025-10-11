# core/export_docx_template.py
from typing import Dict, Any, List, Optional
import regex as re
from docx import Document
from docx.text.paragraph import Paragraph
from docx.oxml import OxmlElement

# =============================
# --- Utilidades internas ---
# =============================

NBSP = "\u00A0"
ZWSP = "\u200B"
SOFT = "\u00AD"


def _clean_text(s: str) -> str:
    if not s:
        return ""
    return s.replace(NBSP, " ").replace(ZWSP, "").replace(SOFT, "")


def _chunks(s: str, n: int = 3000):
    for i in range(0, len(s), n):
        yield s[i:i + n]


def _para_full_text(p: Paragraph) -> str:
    if getattr(p, "runs", None):
        return "".join(r.text or "" for r in p.runs)
    return p.text or ""


def _clear_paragraph(p: Paragraph):
    for r in list(p.runs or []):
        r.text = ""
        try:
            r._element.getparent().remove(r._element)
        except Exception:
            pass
    try:
        p._p.clear_content()
    except Exception:
        pass


def _insert_paragraph_after(p: Paragraph, text: str = "") -> Paragraph:
    new_p = OxmlElement("w:p")
    p._p.addnext(new_p)
    new_para = Paragraph(new_p, p._parent)
    if text:
        for chunk in _chunks(text):
            new_para.add_run(chunk)
    return new_para


# =============================
# --- Reemplazo de texto ---
# =============================

def _write_paragraphs(para: Paragraph, text: str):
    """
    Escribe texto respetando saltos de párrafo (\n\n) y manteniendo el resto del documento.
    """
    raw = _clean_text(text or "")
    blocks = [b.strip() for b in raw.split("\n\n") if b.strip()]
    if not blocks:
        _clear_paragraph(para)
        return

    next_elem = para._p.getnext()

    _clear_paragraph(para)
    for chunk in _chunks(blocks[0]):
        para.add_run(chunk)

    cur = para
    for b in blocks[1:]:
        cur = _insert_paragraph_after(cur, "")
        for chunk in _chunks(b):
            cur.add_run(chunk)

    if next_elem is not None and cur._p.getnext() != next_elem:
        cur._p.addnext(next_elem)


def _iter_paragraphs(doc: Document):
    """Itera todos los párrafos del documento y sus tablas."""
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


def _replace_placeholders(doc: Document, replacements: Dict[str, Any]):
    """
    Sustituye todos los placeholders {{ key }} en el documento.
    """
    for para in _iter_paragraphs(doc):
        text = _clean_text(_para_full_text(para))
        if "{{" not in text:
            continue

        for key, value in replacements.items():
            pattern = re.compile(r"\{\{\s*" + re.escape(key) + r"\s*\}\}", flags=re.DOTALL)

            # Si el párrafo contiene solo ese placeholder
            if pattern.fullmatch(text.strip()):
                _write_paragraphs(para, str(value or ""))
                break

            # Si está dentro de texto normal
            elif pattern.search(text):
                new_text = pattern.sub(str(value or ""), text)
                _clear_paragraph(para)
                for chunk in _chunks(new_text):
                    para.add_run(chunk)
                break


# =============================
# --- Tablas con etiquetas ---
# =============================

def _norm_label(s: str) -> str:
    s = _clean_text(s or "").lower().strip()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def _fill_tables_by_labels(doc: Document, data: Dict[str, Any]):
    """
    Busca tablas con 2 columnas y rellena las celdas derechas
    si la etiqueta izquierda coincide con una clave del diccionario.
    """
    for t in doc.tables:
        for r in t.rows:
            if len(r.cells) < 2:
                continue
            label = _norm_label(_para_full_text(r.cells[0]))
            if label in data and data[label]:
                _clear_paragraph(r.cells[1].paragraphs[0])
                r.cells[1].paragraphs[0].add_run(str(data[label]))


# =============================
# --- API principal ---
# =============================

def export_docx_from_placeholder_map(
    placeholder_map: Dict[str, Any],
    plantilla_path: str,
    out_path: str,
    *,
    label_values: Optional[Dict[str, Any]] = None
) -> str:
    """
    Reemplaza placeholders {{ key }} y rellena tablas de 2 columnas por etiquetas.
    """
    doc = Document(plantilla_path)

    replacements = {str(k): str(v or "") for k, v in (placeholder_map or {}).items()}
    replacements.pop("tabla_coordenadas", None)

    _replace_placeholders(doc, replacements)
    _fill_tables_by_labels(doc, label_values or placeholder_map)

    doc.save(out_path)
    return out_path
