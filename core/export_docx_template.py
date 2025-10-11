# core/export_docx_template.py
from typing import Dict, Tuple, List, Optional, Any
import regex as re  # más robusto que 're' con unicode
from docx import Document
from docx.text.paragraph import Paragraph
from docx.oxml import OxmlElement

# ------------------ caracteres problemáticos típicos de Word -------------------
NBSP = "\u00A0"   # no-break space
ZWSP = "\u200B"   # zero-width space
SOFT = "\u00AD"   # soft hyphen
WS   = r"(?:[\s\u00A0\u200B]*)"  # clase de espacios para patrones {{  key  }}

# ------------------------------------------------------------------------------
# Utilidades de texto / párrafos
# ------------------------------------------------------------------------------

def _chunks(s: str, n: int = 3000):
    for i in range(0, len(s), n):
        yield s[i:i+n]

def _clean_for_match(s: str) -> str:
    if s is None:
        return ""
    return s.replace(NBSP, " ").replace(ZWSP, "").replace(SOFT, "")

def _flatten_inline(s: str) -> str:
    s = _clean_for_match(s or "")
    s = s.replace("\r", " ").replace("\n", " ")
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()

def _para_full_text(para: Paragraph) -> str:
    if getattr(para, "runs", None):
        return "".join(r.text or "" for r in para.runs)
    return para.text or ""

def _clear_paragraph(para: Paragraph):
    for r in list(para.runs or []):
        r.text = ""
        try:
            r._element.getparent().remove(r._element)
        except Exception:
            pass
    try:
        para._p.clear_content()
    except Exception:
        pass

def _insert_paragraph_after(para: Paragraph, text: str = "") -> Paragraph:
    new_p = OxmlElement("w:p")
    para._p.addnext(new_p)
    new_para = Paragraph(new_p, para._parent)
    if text:
        for chunk in _chunks(text):
            new_para.add_run(chunk)
    return new_para

def _write_paragraphs(para: Paragraph, text_with_paras: str):
    raw = _clean_for_match(text_with_paras or "")
    blocks = raw.split("\n\n")
    blocks = [re.sub(r"[ \t]+", " ", b.strip()) for b in blocks if b is not None]

    _clear_paragraph(para)
    if not blocks:
        return

    for chunk in _chunks(blocks[0]):
        para.add_run(chunk)

    cur = para
    for b in blocks[1:]:
        cur = _insert_paragraph_after(cur, "")
        for chunk in _chunks(b):
            cur.add_run(chunk)

def _text_blocks(s: str) -> List[str]:
    """
    Convierte un texto en bloques de párrafo:
    - '\n\n' separa párrafos reales.
    - Dentro de cada bloque, los saltos simples '\n' se aplanan a espacio.
    """
    raw = _clean_for_match(s or "")
    parts = raw.split("\n\n")
    blocks = []
    for p in parts:
        p = p.replace("\r", " ")
        p = re.sub(r"\n+", " ", p)         # aplanar saltos simples
        p = re.sub(r"[ \t]+", " ", p).strip()
        if p:
            blocks.append(p)
    return blocks

# ------------------------------------------------------------------------------
# Reemplazo robusto de placeholders {{ key }}
# ------------------------------------------------------------------------------

def _compile_patterns(placeholders: Dict[str, str]) -> Dict[str, Tuple[re.Pattern, str, re.Pattern]]:
    compiled = {}
    for key, val in (placeholders or {}).items():
        pat_inline = re.compile(r"\{\{" + WS + re.escape(key) + WS + r"\}\}")
        pat_block  = re.compile(r"^" + WS + r"\{\{" + WS + re.escape(key) + WS + r"\}\}" + WS + r"$")
        compiled[key] = (pat_inline, ("" if val is None else str(val)), pat_block)
    return compiled

def _para_has_breaks(para: Paragraph) -> bool:
    """True si el párrafo contiene <w:br/> o <w:cr/> (Shift+Enter en Word)."""
    try:
        ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        return bool(para._p.xpath(".//w:br | .//w:cr", namespaces=ns))
    except Exception:
        return False


def _is_only_this_placeholder(cleaned_text: str, placeholder: str) -> bool:
    """True si el texto limpio es exclusivamente {{ placeholder }} (tolerando espacios)."""
    pat = re.compile(r"^\s*\{\{\s*" + re.escape(placeholder) + r"\s*\}\}\s*$")
    return bool(pat.match(cleaned_text))

def _replace_in_paragraph(para: Paragraph, compiled: Dict[str, Tuple[re.Pattern, str, re.Pattern]]) -> bool:
    """
    Reemplaza tokens {{ key }} dentro del MISMO párrafo respetando cualquier
    texto antes/después del token. Si el valor trae '\n\n', el primer bloque
    queda en el párrafo y los siguientes se insertan como párrafos NUEVOS
    DESPUÉS del actual. No se borra más contenido del debido.
    """
    original = _para_full_text(para)
    if not original:
        return False
    text = _clean_for_match(original)

    changed = False

    # Intento 1: reemplazo token por token (inline seguro)
    for key, (pat_inline, value, pat_block) in compiled.items():
        # buscamos TODAS las ocurrencias de ESTE token en el texto limpio
        # y proyectamos los índices sobre 'original' por simple replace de string,
        # evitando manipular runs a mano: trabajamos con el texto plano y luego rescribimos.
        token_matches = list(pat_inline.finditer(text))
        if not token_matches:
            continue

        # vamos construyendo el nuevo texto de este párrafo
        pieces: List[str] = []
        last_idx = 0
        for m in token_matches:
            before = text[last_idx:m.start()]
            pieces.append(before)

            # bloque de valor
            val_raw = value or ""
            blocks = _clean_for_match(val_raw).split("\n\n")
            blocks = [re.sub(r"[ \t]+", " ", b.strip()) for b in blocks if b is not None]

            # el primer bloque queda en-línea en ESTE párrafo (aplanado)
            first_inline = _flatten_inline(blocks[0] if blocks else "")
            pieces.append(first_inline)

            last_idx = m.end()

            # si hay bloques extra, los insertamos como párrafos NUEVOS después del actual
            # (no tocamos todavía el doc; sólo marcamos que hay que insertarlos)
            extra_blocks = blocks[1:]

            if extra_blocks:
                # Escribimos todo lo que quedaba "después" del token en ESTE párrafo
                after_text = text[last_idx:]
                # reconstruimos el párrafo actual con lo que llevamos + resto
                new_text_current = "".join(pieces) + after_text

                # Reseteamos el párrafo actual y lo escribimos
                _clear_paragraph(para)
                for chunk in _chunks(new_text_current):
                    para.add_run(chunk)

                # Insertamos cada bloque extra como párrafos nuevos, en orden
                cur = para
                for b in extra_blocks:
                    cur = _insert_paragraph_after(cur, "")
                    for chunk in _chunks(b):
                        cur.add_run(chunk)

                # Hemos reescrito el párrafo; toca recalcular 'text' y reiniciar ciclo
                original = _para_full_text(para)
                text = _clean_for_match(original)
                pieces = []
                last_idx = 0
                changed = True
                break  # reiniciamos el bucle exterior sobre compiled (nuevo 'text')

        else:
            # No hubo bloques extra -> podemos terminar reconstruyendo el párrafo una vez
            if pieces or token_matches:
                pieces.append(text[last_idx:])
                new_text = "".join(pieces)
                if new_text != text:
                    _clear_paragraph(para)
                    for chunk in _chunks(new_text):
                        para.add_run(chunk)
                    text = new_text  # para siguientes claves
                    changed = True

    return changed


def _iter_all_paragraphs(doc: Document):
    """Itera TODOS los párrafos del documento (cuerpo, tablas, headers y footers)."""
    # cuerpo
    for p in doc.paragraphs:
        yield p
    # tablas del cuerpo
    for t in doc.tables:
        for r in t.rows:
            for c in r.cells:
                for p in c.paragraphs:
                    yield p
    # headers / footers
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

def _replace_placeholder_block_everywhere(doc: Document, replacements: Dict[str, str]) -> List[str]:
    compiled = _compile_patterns(replacements)
    changed_refs: List[str] = []

    while True:
        changed_this_pass = False
        for para in _iter_all_paragraphs(doc):
            t = _clean_for_match(_para_full_text(para))
            if "{{" not in t:
                continue
            before = t
            if _replace_in_paragraph(para, compiled):
                changed_this_pass = True
                changed_refs.append(before[:80])
        if not changed_this_pass:
            break

    return changed_refs


# ------------------------------------------------------------------------------
# Relleno por ETIQUETAS (tablas 2 columnas) sin placeholders
# ------------------------------------------------------------------------------

def _norm_label(s: str) -> str:
    s = _clean_for_match(s or "")
    s = s.lower().strip()
    s = re.sub(r"[:\.\-,]+", "", s)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[áàä]", "a", s)
    s = re.sub(r"[éèë]", "e", s)
    s = re.sub(r"[íìï]", "i", s)
    s = re.sub(r"[óòö]", "o", s)
    s = re.sub(r"[úùü]", "u", s)
    s = s.replace("º", "").replace("ª", "")
    return s

def _first_cell_text(cell) -> str:
    txts = []
    for p in cell.paragraphs:
        txts.append(_clean_for_match(_para_full_text(p)))
    return " ".join(txts).strip()

def _write_cell_text(cell, text: str):
    # sobrescribe limpiamente el contenido de una celda
    for p in list(cell.paragraphs):
        _clear_paragraph(p)
    if not cell.paragraphs:
        cell.add_paragraph("")
    p = cell.paragraphs[0]
    for chunk in _chunks(text or ""):
        p.add_run(chunk)

def _fmt_num(v: Any) -> str:
    if v is None:
        return ""
    try:
        f = float(v)
        return str(int(f)) if abs(f - int(f)) < 1e-9 else str(f)
    except Exception:
        return str(v)

def _label_alias_map() -> Dict[str, List[str]]:
    """
    Mapa de etiqueta normalizada -> lista de claves candidatas en placeholder_map/label_values.
    Se prueban en orden y se escoge la primera que tenga valor no vacío.
    """
    return {
        # Coordenadas
        "utm x":                ["utm_x_principal", "coordenadas.utm.x", "utm_x"],
        "utm y":                ["utm_y_principal", "coordenadas.utm.y", "utm_y"],
        "huso":                 ["utm_huso_principal", "coordenadas.utm.huso", "huso"],
        "datum":                ["coordenadas.utm.datum", "datum"],
        "latitud":              ["geo_lat_principal", "coordenadas.geo.lat", "latitud"],
        "longitud":             ["geo_lon_principal", "coordenadas.geo.lon", "longitud"],
        # Localización
        "municipio":            ["municipio", "localizacion.municipio"],
        "provincia":            ["provincia", "localizacion.provincia"],
        # Parámetros
        "profundidad":          ["profundidad", "parametros.profundidad", "parametros.profundidad_proyectada_m"],
        "diametro inicial":     ["diametro_inicial", "parametros.diametro_inicial", "diámetro_inicial"],
        "diametro perforacion inicial mm":
                                 ["diametro_perforacion_inicial_mm", "parametros.diametro_perforacion_inicial_mm"],
        "caudal max instantaneo l s":
                                 ["caudal_max_instantaneo_l_s", "parametros.caudal_max_instantaneo_l_s"],
        "instalacion electrica":["instalacion_electrica", "parametros.instalacion_electrica"],
        "potencia bombeo kw":   ["potencia_bombeo_kw", "parametros.potencia_bombeo_kw"],
    }

def _get_from_map(data_map: Dict[str, Any], key: str) -> Optional[str]:
    # acceso simple y por rutas a.b.c
    if key in data_map:
        return data_map.get(key)
    if "." in key:
        cur: Any = data_map
        for k in key.split("."):
            if not isinstance(cur, dict):
                return None
            cur = cur.get(k)
        return cur
    return None

def _fill_tables_by_labels(doc: Document, placeholder_map: Dict[str, Any], label_values: Optional[Dict[str, Any]] = None) -> List[str]:
    """
    Recorre TODAS las tablas. Para cada fila con 2 columnas:
    - Normaliza la etiqueta de la primera celda.
    - Si hay una clave candidata con valor (en label_values o placeholder_map), escribe en la celda derecha.
    Devuelve lista de etiquetas rellenadas (debug).
    """
    aliases = _label_alias_map()
    filled: List[str] = []

    # conjunto de datos donde buscar: primero label_values (si viene), luego placeholder_map
    sources = [label_values or {}, placeholder_map or {}]

    for t in doc.tables:
        for r in t.rows:
            if len(r.cells) < 2:
                continue
            left = _first_cell_text(r.cells[0])
            lab = _norm_label(left)
            if not lab:
                continue

            if lab in aliases:
                # busca primer valor no vacío entre todas las fuentes y alias
                value = ""
                for cand in aliases[lab]:
                    for src in sources:
                        v = _get_from_map(src, cand)
                        if v not in (None, "", []):
                            value = str(v)
                            break
                    if value:
                        break

                if value != "":
                    _write_cell_text(r.cells[1], _fmt_num(value))
                    filled.append(lab)

    return filled

# ------------------------------------------------------------------------------
# API principal
# ------------------------------------------------------------------------------

def export_docx_from_placeholder_map(
    placeholder_map: Dict[str, Any],
    plantilla_path: str,
    out_path: str,
    *,
    label_values: Optional[Dict[str, Any]] = None
) -> str:
    """
    1) Reemplaza placeholders {{ key }} en cuerpo, tablas, encabezados y pies.
       - Soporta runs partidos, NBSP/ZWSP/SOFT.
       - Párrafo = solo placeholder -> respeta '\n\n' como nuevos párrafos.
       - INLINE 'block-aware' conserva texto antes/después y crea párrafos por '\n\n'.
       - Inline normal aplanando '\n' cuando no hay '\n\n' en el valor.
    2) Rellena tablas 2 columnas por ETIQUETAS (sin placeholders).
    Limitación:
      - python-docx no entra en cuadros de texto/WordArt (w:drawing → txbxContent).
    """
    doc = Document(plantilla_path)

    # 1) Placeholder replacement
    replacements = {str(k): ("" if v is None else str(v)) for k, v in (placeholder_map or {}).items()}
    _replace_placeholder_block_everywhere(doc, replacements)

    # 2) Label-based filling (sin placeholders)
    _fill_tables_by_labels(doc, placeholder_map, label_values=label_values)

    # 3) Guardar
    doc.save(out_path)
    return out_path
