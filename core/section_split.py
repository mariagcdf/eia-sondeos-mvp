# core/section_split.py
# Divide el texto en secciones (por encabezados) y selecciona las que queremos copiar literal

import re
from typing import Dict, List

SECTION_HEAD_HINTS = [
    "introducción", "antecedentes", "objeto", "situación",
    "geología", "hidrogeología",
    "características del sondeo", "realización del sondeo",
    "explotación", "instalación eléctrica",
    "pliego de condiciones",
    "estudio básico de seguridad", "estudio básico de seguridad y salud",
    "presupuesto", "mediciones", "precios unitarios", "presupuesto total",
]

LITERAL_SECTION_PATTERNS = [
    r"\bsituaci[oó]n\b",
    r"\bgeolog[ií]a\b",
    r"\bhidrogeolog[ií]a\b",
    r"\bcaracter[íi]sticas\b.*sondeo",
    r"\brealizaci[oó]n\b.*sondeo",
    r"\bexplotaci[oó]n\b",
    r"\binstalaci[oó]n el[eé]ctrica\b",
    r"\bpliego de condiciones\b",
    r"\bestudio b[aá]sico de seguridad\b",
    r"\bpresupuesto\b",
]


def split_into_sections(text: str) -> Dict[str, str]:
    """Divide un texto largo en secciones según encabezados."""
    lines = text.split("\n")
    sections: Dict[str, List[str]] = {}
    current = "_inicio"
    sections[current] = []

    def is_header(line: str) -> bool:
        l = line.lower().strip()
        if not l:
            return False
        if re.match(r"^\d+(\.\d+)*\s*[\.\-–—]?\s+.+", l):
            return True
        return any(h in l for h in SECTION_HEAD_HINTS)

    def norm_title(line: str) -> str:
        return re.sub(r"\s+", " ", line.strip())

    for ln in lines:
        if is_header(ln):
            current = norm_title(ln)
            if current not in sections:
                sections[current] = []
        sections[current].append(ln)

    return {k: "\n".join(v).strip() for k, v in sections.items() if v}


def pick_literal_sections(sections: Dict[str, str]) -> Dict[str, str]:
    """Selecciona las secciones que queremos copiar literal en la EIA."""
    out: Dict[str, str] = {}
    for title, body in sections.items():
        tl = title.lower()
        if any(re.search(pat, tl, flags=re.I) for pat in LITERAL_SECTION_PATTERNS):
            out[title] = body
    return out
