from typing import Dict, List
import re

def extraer_bloques_literal(texto_completo: str) -> Dict[str, str]:
    """
    Devuelve SOLO bloques textuales largos:
    - PH_Antecedentes
    - PH_Situacion
    - PH_Consumo
    - geologia

    Conserva párrafos reales (doble salto), aplana saltos simples.
    """
    NBSP = "\u00A0"
    SOFT_HYPHEN = "\u00AD"

    def _sanitize_pdf_text(s: str) -> str:
        if not s:
            return ""
        s = s.replace("\r", "\n").replace(NBSP, " ").replace(SOFT_HYPHEN, "")
        s = re.sub(r"(?<=\w)-\n(?=\w)", "", s)
        s = re.sub(r"Pl\.\s*San\s*Crist[oó]bal[^\n]+ipsaingenieros\.com", "", s, flags=re.I)
        s = re.sub(r"---\s*P[aá]gina\s*\d+\s*---", "", s, flags=re.I)
        s = re.sub(r"[ \t]+", " ", s)
        s = re.sub(r"\n{3,}", "\n\n", s)
        return s.strip()

    def _quitar_lineas_indice(t: str) -> str:
        out = []
        for line in t.splitlines():
            L = line.strip()
            if re.search(r"\.{3,}\s*\d{1,4}\s*$", L):  # “..... 12”
                continue
            if re.search(r"^\s*(Contenido|Índice)\s*:?\s*$", L, re.IGNORECASE):
                continue
            out.append(line)
        return "\n".join(out)

    def _keep_paragraphs_drop_linebreaks(s: str) -> str:
        s = (s or "").replace("<br />", "\n").replace("<br/>", "\n").replace("<br>", "\n")
        s = s.replace("\r", "\n")
        s = re.sub(r"\n{3,}", "\n\n", s)
        s = re.sub(r'(?<!\n)\n(?!\n)', ' ', s)   # salto simple -> espacio
        s = re.sub(r"[ \t]+", " ", s)
        s = re.sub(r"\n{3,}", "\n\n", s)
        return s.strip()

    def _strip_heading(s: str, palabras: List[str]) -> str:
        if not s:
            return ""
        pat = rf"^\s*(?:\d+\s*[.,)]?\s*\d*\s*[.)]?\s*)?(?:{'|'.join(map(re.escape, palabras))})\s*[:.\-–—]?\s*"
        return re.sub(pat, "", s, count=1, flags=re.IGNORECASE).strip()

    def _find_first(text: str, patterns: List[str], start: int) -> int:
        end = len(text)
        for p in patterns:
            m = re.search(p, text[start:], flags=re.IGNORECASE)
            if m:
                end = min(end, start + m.start())
        return end

    # ---- Limpieza base
    t = _sanitize_pdf_text(texto_completo or "")
    t = _quitar_lineas_indice(t)

    # ---- ANTECEDENTES
    antecedentes = ""
    for p in [
        r"(?m)^\s*1[.,]?\s*1\b.*Antecedentes",
        r"(?m)^\s*1[.,]?\s*Introducci[oó]n\b",
        r"(?m)^\s*Cap[ií]tulo\s*1\b.*Introducci[oó]n",
        r"(?m)^\s*Antecedentes\b",
    ]:
        m = re.search(p, t, flags=re.IGNORECASE | re.MULTILINE)
        if m:
            start = m.start()
            end = _find_first(t, [
                r"Se\s+justifica",
                r"(?m)^\s*1[.,]?\s*2\b", r"(?m)^\s*Objeto\b",
                r"(?m)^\s*2[.,]?\s*0?\b", r"(?m)^\s*Situaci[oó]n\b",
                r"(?m)^\s*Emplazamiento\b",
            ], start)
            antecedentes = _keep_paragraphs_drop_linebreaks(
                _strip_heading(t[start:end].strip(), ["Antecedentes", "Introducción"])
            )
            break

    # ---- SITUACIÓN  (PH_Situacion con S mayúscula, sin duplicados)
    situacion = ""
    for p in [
        r"(?m)^\s*1[.,]?\s*3\b.*Situaci[oó]n",
        r"(?m)^\s*2[.,]?\s*1\b.*Situaci[oó]n",
        r"(?m)^\s*Situaci[oó]n\b",
        r"(?m)^\s*Emplazamiento\b",
        r"(?m)^\s*Ubicaci[oó]n\b",
    ]:
        m = re.search(p, t, flags=re.IGNORECASE | re.MULTILINE)
        if m:
            start = m.start()
            end = _find_first(t, [
                r"Las\s+coordenadas",
                r"\bU\.?\s*T\.?\s*M\.?\b",
                r"\bX\s*=\s*\d",
                r"\bLatitud\s*=",
                r"\bLongitud\s*=",
                r"Coordenadas\s+ETRS",
                r"El\s+sondeo\s+(existente|nuevo)",
                r"(?m)^\s*1[.,]?\s*4\b",
                r"(?m)^\s*GEOLOG",
            ], start)
            situacion = _keep_paragraphs_drop_linebreaks(
                _strip_heading(t[start:end].strip(), ["Situación del sondeo", "Situación", "Ubicación", "Emplazamiento"])
            )
            break

    # ---- CONSUMO
    def _planito(s: str) -> str:
        return re.sub(r"\s+", " ", (s or "")).strip()

    consumo = ""
    m = re.search(r"(?m)^\s*3[.,]?\s*1\b.*(Consumo|Caudal\s+necesario|Demanda)\b", t, re.I)
    if not m:
        m = re.search(r"(?m)^\s*(Consumo|Caudal\s+necesario|Demanda)\b", t, re.I)
    if m:
        start = m.start()
        end = _find_first(t, [
            r"(?m)^\s*3[.,]?\s*2\b", r"(?m)^\s*4[.,]?\s*\b",
            r"(?m)^\s*REALIZACI[ÓO]N\b", r"(?m)^\s*Instalaci[oó]n"
        ], start)
        consumo = _planito(t[start:end])

    # ---- GEOLOGÍA
    geologia = ""
    m = re.search(r"(?m)^\s*(GEOLOG[ÍI]A\s*E?\s*HIDROGEOLOG[ÍI]A|Geolog[ií]a|Hidrogeolog[ií]a)\b", t, re.I)
    if m:
        start = m.start()
        end = _find_first(t, [
            r"(?m)^\s*3[.,]?\s*\b", r"(?m)^\s*CARACTER[ÍI]STICAS\b",
            r"(?m)^\s*REALIZACI[ÓO]N\b", r"(?m)^\s*4[.,]?\s*\b",
            r"(?m)^\s*Valores\s+ambientales\b"
        ], start)
        geologia = _planito(t[start:end])

    # ---- SALIDA (sin alternativas, sin municipio/provincia aquí)
    return {
        "PH_Antecedentes": antecedentes,
        "PH_Localizacion": situacion,
        "PH_Consumo": consumo,
        "geologia": geologia,
    }
