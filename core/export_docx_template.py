# core/export_docx_template.py
# Recibe un JSON (placeholder -> valor) y lo vuelca en el DOCX
# con soporte de textos largos: crea párrafos y saltos de línea reales.

from typing import Dict, Any
from docx import Document

# ----------------------------
# Motor de volcado de TEXTO LARGO
# ----------------------------

def _chunks(s: str, n: int = 3000):
    for i in range(0, len(s), n):
        yield s[i:i+n]

def _clear_paragraph(para):
    # Borra todos los runs del párrafo
    for r in para.runs:
        r.text = ""
    # Elimina runs para dejar el párrafo limpio
    while para.runs:
        para.runs[0]._element.getparent().remove(para.runs[0]._element)

def _set_paragraph_text_with_linebreaks(para, text: str):
    """
    Escribe 'text' en 'para':
    - '\n\n' -> nuevo párrafo
    - '\n'   -> salto de línea (w:br)
    - Trocea en runs (~3000 chars) para evitar límites de run
    """
    _clear_paragraph(para)
    text = (text or "").replace("\r", "\n")
    blocks = text.split("\n\n")

    def fill_one(dst_para, txt: str):
        lines = txt.split("\n")
        for li_i, line in enumerate(lines):
            # Añade contenido en trozos
            for chunk in _chunks(line):
                dst_para.add_run(chunk)
            # Si hay más líneas, salto de línea real
            if li_i < len(lines) - 1:
                run = dst_para.add_run()
                run.add_break()

    # Primer bloque en el párrafo actual
    fill_one(para, blocks[0])

    # Resto como párrafos nuevos
    cur = para
    for b in blocks[1:]:
        new_p = cur.insert_paragraph_after("")
        fill_one(new_p, b)
        cur = new_p

def _replace_placeholder_block_in_paragraph(para, placeholder: str, value: str) -> bool:
    """
    Si el párrafo contiene {{placeholder}}, lo reemplaza por 'value'.
    Si el placeholder ocupa TODO el párrafo, expande '\n' en párrafos/saltos.
    Devuelve True si hizo reemplazo.
    """
    full_text = "".join(r.text for r in para.runs)
    token = f"{{{{{placeholder}}}}}"
    if token not in full_text:
        return False

    before, sep, after = full_text.partition(token)

    # Párrafo formado SOLO por el placeholder -> expansión bonita
    if before == "" and after == "":
        _set_paragraph_text_with_linebreaks(para, str(value or ""))
        return True

    # Inline -> reemplazo simple en el mismo párrafo (troceado en runs)
    new_text = full_text.replace(token, str(value or ""))
    _clear_paragraph(para)
    for chunk in _chunks(new_text):
        para.add_run(chunk)
    return True

def _replace_placeholder_block_everywhere(doc: Document, replacements: Dict[str, str]):
    """
    Reemplaza en cuerpo, tablas, encabezados y pies.
    Usa el motor de bloque largo que crea párrafos/saltos si procede.
    """
    # cuerpo
    for para in doc.paragraphs:
        if "{{" in para.text:
            for k, v in replacements.items():
                _replace_placeholder_block_in_paragraph(para, k, v)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    if "{{" in para.text:
                        for k, v in replacements.items():
                            _replace_placeholder_block_in_paragraph(para, k, v)

    # headers / footers
    for section in doc.sections:
        # header
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
        # footer
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


# ----------------------------
# Exportador simple (sin bridges)
# ----------------------------

def export_docx_from_placeholder_map(
    placeholder_map: Dict[str, str],
    plantilla_path: str,
    out_path: str
) -> str:
    """
    Recibe el JSON {placeholder: valor} y lo inyecta en la plantilla.
    Soporta textos largos (crea párrafos y saltos).
    """
    doc = Document(plantilla_path)
    # Solo strings en el mapa final
    replacements = {k: ("" if v is None else str(v)) for k, v in (placeholder_map or {}).items()}
    _replace_placeholder_block_everywhere(doc, replacements)
    doc.save(out_path)
    return out_path
