# core/export_docx_template.py
# Recibe un JSON (placeholder -> valor) y lo vuelca en el DOCX
# con soporte de textos largos y estructura (párrafos, saltos, listas).

from typing import Dict, Any, List
from docx import Document
from docx.text.paragraph import Paragraph
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

# =========================
# Utilidades internas
# =========================

def _chunks(s: str, n: int = 3000):
    for i in range(0, len(s), n):
        yield s[i:i+n]

def _clear_paragraph(para: Paragraph):
    # Borra el contenido manteniendo estilo y propiedades del párrafo
    for r in para.runs:
        r.text = ""
    # Elimina los runs (deja el párrafo limpio)
    while para.runs:
        para.runs[0]._element.getparent().remove(para.runs[0]._element)

def _add_paragraph_after(para: Paragraph, text: str = "", style: str = None) -> Paragraph:
    """
    Inserta un párrafo justo después de 'para' (compatible con python-docx).
    Devuelve el nuevo Paragraph.
    """
    p = para._element
    new_p = OxmlElement("w:p")
    p.addnext(new_p)
    new_para = Paragraph(new_p, para._parent)
    if style:
        try:
            new_para.style = style
        except Exception:
            pass
    if text:
        for chunk in _chunks(text):
            new_para.add_run(chunk)
    return new_para

def _is_bullet_line(line: str) -> bool:
    return line.strip().startswith("- ")

def _is_numbered_line(line: str) -> bool:
    s = line.strip()
    # 1. texto  |  1) texto
    return True if len(s) > 2 and (s[0].isdigit() and (s[1] in ".)")) else False

def _strip_bullet_prefix(line: str) -> str:
    return line.strip()[2:] if line.strip().startswith("- ") else line

def _strip_number_prefix(line: str) -> str:
    s = line.strip()
    i = 0
    while i < len(s) and s[i].isdigit():
        i += 1
    if i < len(s) and s[i] in (".", ")"):
        i += 1
    return s[i:].lstrip()

def _write_plain_block(dst_para: Paragraph, txt: str):
    """
    Escribe un bloque de varias líneas en un único párrafo insertando saltos reales (w:br).
    """
    lines = txt.split("\n")
    _clear_paragraph(dst_para)
    for li_i, line in enumerate(lines):
        for chunk in _chunks(line):
            dst_para.add_run(chunk)
        if li_i < len(lines) - 1:
            run = dst_para.add_run()
            run.add_break()

def _write_list_block(first_para: Paragraph, lines: List[str], list_style: str):
    """
    Crea una lista (viñetas o numerada). El primer item reutiliza 'first_para';
    el resto se insertan después, cada uno en su nuevo párrafo con 'list_style'.
    """
    # Limpia y convierte el párrafo actual en el primer punto de lista
    _clear_paragraph(first_para)
    try:
        first_para.style = list_style
    except Exception:
        pass

    first_line = lines[0]
    content = _strip_bullet_prefix(first_line) if list_style == "List Bullet" else _strip_number_prefix(first_line)
    for chunk in _chunks(content):
        first_para.add_run(chunk)

    # Resto de items
    cur = first_para
    for line in lines[1:]:
        txt = _strip_bullet_prefix(line) if list_style == "List Bullet" else _strip_number_prefix(line)
        cur = _add_paragraph_after(cur, "", style=list_style)
        for chunk in _chunks(txt):
            cur.add_run(chunk)

def _set_paragraph_text_with_structure(para: Paragraph, text: str):
    """
    Escribe 'text' en 'para' con estructura:
    - Bloques separados por '\n\n' -> párrafos separados.
    - Dentro de cada bloque:
        * Si la mayoría de líneas empiezan por '- ' => lista con viñetas (List Bullet).
        * Si la mayoría son '1. ' / '1) ' => lista numerada (List Number).
        * Si no, párrafo normal con saltos de línea reales.
    """
    text = (text or "").replace("\r", "\n")
    blocks = text.split("\n\n")

    # Primer bloque en 'para'
    first_block = blocks[0]
    lines = [ln for ln in first_block.split("\n") if ln.strip() != ""]

    if not lines:
        _write_plain_block(para, "")
    else:
        bullets = sum(1 for ln in lines if _is_bullet_line(ln))
        numbers = sum(1 for ln in lines if _is_numbered_line(ln))

        if bullets > max(numbers, 0) and bullets >= 2:
            _write_list_block(para, lines, "List Bullet")
        elif numbers > max(bullets, 0) and numbers >= 2:
            _write_list_block(para, lines, "List Number")
        else:
            _write_plain_block(para, first_block)

    # Resto de bloques (párrafos nuevos)
    cur = para
    for b in blocks[1:]:
        lines_b = [ln for ln in b.split("\n") if ln.strip() != ""]
        if not lines_b:
            cur = _add_paragraph_after(cur, "")  # párrafo vacío (se respeta doble salto)
            continue

        bullets_b = sum(1 for ln in lines_b if _is_bullet_line(ln))
        numbers_b = sum(1 for ln in lines_b if _is_numbered_line(ln))

        if bullets_b > max(numbers_b, 0) and bullets_b >= 2:
            # crear lista completa partiendo de un nuevo párrafo
            cur = _add_paragraph_after(cur, "", style="List Bullet")
            _write_list_block(cur, lines_b, "List Bullet")
            # al terminar _write_list_block, 'cur' apunta al primer item; movemos al último
            # (añadiendo un párrafo vacío no es necesario; el siguiente _add_paragraph_after insertará donde toca)
            # localizar último item: avanzamos items-1 veces
            for _ in range(len(lines_b) - 1):
                cur = cur._p.getnext()  # tipo oxml
                cur = Paragraph(cur, cur.getparent())  # reconstruir Paragraph
        elif numbers_b > max(bullets_b, 0) and numbers_b >= 2:
            cur = _add_paragraph_after(cur, "", style="List Number")
            _write_list_block(cur, lines_b, "List Number")
            for _ in range(len(lines_b) - 1):
                cur = cur._p.getnext()
                cur = Paragraph(cur, cur.getparent())
        else:
            cur = _add_paragraph_after(cur, "")
            _write_plain_block(cur, b)

def _replace_placeholder_block_in_paragraph(para: Paragraph, placeholder: str, value: str) -> bool:
    """
    Si el párrafo contiene {{placeholder}}, lo reemplaza por 'value'.
    Si el placeholder ocupa TODO el párrafo, expande estructura (párrafos/saltos/listas).
    Devuelve True si hizo reemplazo.
    """
    full_text = "".join(r.text for r in para.runs)
    token = f"{{{{{placeholder}}}}}"
    if token not in full_text:
        return False

    before, sep, after = full_text.partition(token)

    # Placeholder SOLO en el párrafo -> expansión con estructura
    if before == "" and after == "":
        _set_paragraph_text_with_structure(para, str(value or ""))
        return True

    # Inline -> reemplazo simple (se mantiene el resto del contenido del párrafo)
    new_text = full_text.replace(token, str(value or ""))
    _clear_paragraph(para)
    for chunk in _chunks(new_text):
        para.add_run(chunk)
    return True

def _replace_placeholder_block_everywhere(doc: Document, replacements: Dict[str, str]):
    """
    Reemplaza en cuerpo, tablas, encabezados y pies.
    Usa motor con estructura (párrafos/saltos/listas) si el placeholder ocupa el párrafo completo.
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
    Soporta textos largos con estructura (párrafos, saltos, listas).
    """
    doc = Document(plantilla_path)
    # Solo strings en el mapa final
    replacements = {k: ("" if v is None else str(v)) for k, v in (placeholder_map or {}).items()}
    _replace_placeholder_block_everywhere(doc, replacements)
    doc.save(out_path)
    return out_path
