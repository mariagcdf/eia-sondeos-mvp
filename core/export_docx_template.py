from typing import Dict, Any, Optional
from docx import Document
from docx.text.paragraph import Paragraph
from docx.oxml import OxmlElement
from pathlib import Path
import regex as re
import subprocess
from core.sintesis.alternativas_llm import generar_alternativas_llm
import json

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
    """Extrae el texto completo de un párrafo."""
    return "".join(r.text or "" for r in getattr(p, "runs", [])) or (p.text or "")

def _clear_paragraph_keep_format(p: Paragraph):
    """Vacía un párrafo manteniendo su formato (sangría, alineación, estilo)."""
    for r in list(p.runs):
        r.text = ""
    # No eliminamos los nodos XML, solo el texto

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
# Escritura con saltos
# =====================

def _write_with_paragraphs(para: Paragraph, text: str):
    """
    Escribe texto respetando saltos dobles (\n\n) como nuevos párrafos,
    preservando el formato original del párrafo.
    """
    value = _clean(str(text or ""))
    blocks = [b.strip() for b in value.split("\n\n") if b.strip()]

    fmt = para.paragraph_format
    style = para.style
    alignment = para.alignment

    _clear_paragraph_keep_format(para)
    if not blocks:
        return

    para.add_run(blocks[0])
    para.paragraph_format.left_indent = fmt.left_indent
    para.paragraph_format.first_line_indent = fmt.first_line_indent
    if hasattr(fmt, "hanging_indent"):
        para.paragraph_format.hanging_indent = fmt.hanging_indent
    para.alignment = alignment
    para.style = style

    cur = para
    for b in blocks[1:]:
        cur = _insert_after(cur, b)
        cur.paragraph_format.left_indent = fmt.left_indent
        cur.paragraph_format.first_line_indent = fmt.first_line_indent
        if hasattr(fmt, "hanging_indent"):
            cur.paragraph_format.hanging_indent = fmt.hanging_indent
        cur.alignment = alignment
        cur.style = style


def _replace_placeholders(doc: Document, replacements: Dict[str, Any]):
    """
    Reemplaza todos los {{placeholders}}:
    - Si el párrafo contiene SOLO el marcador → reemplaza el contenido completo.
    - Si hay texto antes o después → reemplazo inline conservando estilo y sangría.
    - Si el párrafo pertenece al encabezado (header), los reemplazos se convierten a mayúsculas reales.
    """
    for para in list(_iter_paragraphs(doc)):
        text = _clean(_para_text(para))
        if "{{" not in text:
            continue

        # 🔹 Detectar si el párrafo pertenece al encabezado del documento
        in_header = False
        try:
            parent = para._element.getparent()
            while parent is not None:
                if parent.tag.endswith("hdr"):  # <w:hdr> → sección de encabezado
                    in_header = True
                    break
                parent = parent.getparent()
        except Exception:
            pass

        for key, val in (replacements or {}).items():
            pattern = re.compile(r"\{\{\s*" + re.escape(key) + r"\s*\}\}", re.DOTALL)
            replacement_text = str(val or "")

            # 🔹 Si el párrafo solo contiene el marcador
            if pattern.fullmatch(text.strip()):
                if in_header:
                    replacement_text = replacement_text.upper()
                _write_with_paragraphs(para, replacement_text)
                break

            # 🔹 Si el marcador está dentro de una línea de texto
            elif pattern.search(text):
                for run in para.runs:
                    if pattern.search(run.text):
                        new_text = pattern.sub(replacement_text, run.text)
                        if in_header:
                            new_text = new_text.upper()  # Forzar mayúsculas solo en encabezado
                        run.text = new_text
                break


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
    Reemplaza todos los {{placeholders}} en runs de texto sin alterar formato.
    - Si el párrafo contiene SOLO el marcador → reemplaza el párrafo entero con nuevos saltos.
    - Si está dentro de una frase o encabezado → reemplazo inline dentro del run.
    """
    for para in list(_iter_paragraphs(doc)):
        text = _clean(_para_text(para))
        if "{{" not in text:
            continue

        for key, val in (replacements or {}).items():
            pattern = re.compile(r"\{\{\s*" + re.escape(key) + r"\s*\}\}", re.DOTALL)

            # Si el párrafo solo contiene el marcador
            if pattern.fullmatch(text.strip()):
                _write_with_paragraphs(para, val)
                break

            # Si el marcador está dentro de una línea de texto (encabezados, frases, etc.)
            for run in para.runs:
                if pattern.search(run.text):
                    run.text = pattern.sub(str(val or ""), run.text)
            # No se limpian runs ni estilos; se actualiza en sitio


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
                    _clear_paragraph_keep_format(r.cells[1].paragraphs[0])
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
    Mantiene formato, sangrías y estilos del párrafo original.
    """

    # 1️⃣ Ejecutar redactor automático antes de exportar
    redactor_script = Path("core/sintesis/redactar_placeholder.py")
    if redactor_script.exists():
        print("🧠 Ejecutando redactor automático de placeholders...")
        try:
            subprocess.run(["python", str(redactor_script)], check=True)
            print("✅ Redacción automática completada.")
        except subprocess.CalledProcessError as e:
            print(f"⚠️ Error ejecutando el redactor automático: {e}")
    else:
        print("⚠️ No se encontró redactar_placeholder.py — se omite la redacción automática.")

     # 2️⃣ Generar Alternativas automáticamente si faltan
    try:
        missing = [k for k in ["PH_Alternativas_Desc", "PH_Alternativas_Val", "PH_Alternativas_Just"]
                   if not placeholder_map.get(k)]
        if missing:
            print(f"🤖 Generando automáticamente las secciones de alternativas: {', '.join(missing)}")
            alt_dict = generar_alternativas_llm(placeholder_map)
            placeholder_map.update(alt_dict)

            # Guardar en el JSON más reciente para persistir los cambios
            output_dir = Path("outputs")
            json_files = sorted(output_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
            if json_files:
                latest_json = json_files[0]
                with open(latest_json, "r+", encoding="utf-8") as f:
                    data = json.load(f)
                    data.update(alt_dict)
                    f.seek(0)
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    f.truncate()
                print(f"💾 Alternativas añadidas al JSON {latest_json.name}")
    except Exception as e:
        print(f"⚠️ Error generando alternativas automáticas: {e}")


    # 2️⃣ Procesar documento
    doc = Document(plantilla_path)
    replacements = {str(k): str(v or "") for k, v in (placeholder_map or {}).items()}

    _replace_placeholders(doc, replacements)
    _fill_tables_by_labels(doc, label_values or placeholder_map)

    doc.save(out_path)
    print(f"📄 Documento exportado correctamente: {out_path}")
    return out_path
