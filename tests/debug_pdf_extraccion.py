import os, re, sys
import pdfplumber

# ---------------------------
# 1) LECTURA DEL PDF
# ---------------------------
def leer_pdf(path_pdf: str) -> str:
    with pdfplumber.open(path_pdf) as pdf:
        partes = []
        for i, p in enumerate(pdf.pages, 1):
            txt = p.extract_text() or ""
            partes.append(f"--- Página {i} ---\n{txt}")
    return "\n".join(partes)


# ---------------------------
# 2) LIMPIEZA BÁSICA
# ---------------------------
def limpiar_texto_basico(t: str) -> str:
    if not t: return ""
    t = t.replace("\r", "\n")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


# ---------------------------
# 3) QUITAR LÍNEAS DE ÍNDICE
# ---------------------------
def quitar_lineas_indice(t: str) -> str:
    out = []
    for line in t.splitlines():
        L = line.strip()
        # heurística: línea con puntos de relleno y número al final
        if re.search(r"\.{3,}\s*\d{1,4}\s*$", L):
            continue
        # encabezado de índice
        if re.search(r"^\s*(Contenido|Índice)\s*:?\s*$", L, re.IGNORECASE):
            continue
        out.append(line)
    return "\n".join(out)


# ---------------------------
# 4) CORTAR DESPUÉS DEL ÍNDICE
# ---------------------------
def cortar_despues_del_indice(t: str) -> str:
    pag_marks = [m.start() for m in re.finditer(r"--- Página \d+ ---", t)]
    pag_marks.append(len(t))
    m = re.search(r"(?im)^\s*Contenido\s*$", t)
    if not m:
        return t
    idx_page = None
    for i in range(len(pag_marks)-1):
        if pag_marks[i] <= m.start() < pag_marks[i+1]:
            idx_page = i
            break
    if idx_page is None:
        return t
    cut_pos = pag_marks[idx_page+1]
    return t[cut_pos:]


# ---------------------------
# 5) FUNCIÓN CORTAR BLOQUE
# ---------------------------
def cortar_bloque_flexible(texto: str, start_keys, stop_keys, window_chars=200):
    start_match = None
    start_pat_used = None
    for s in start_keys:
        m = re.search(s, texto, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if m:
            start_match = m
            start_pat_used = s
            break
    if not start_match:
        print("⚠️  No se encontró inicio con los patrones dados.")
        return ""
    start = start_match.start()

    stop = len(texto)
    stop_pat_used = None
    for e in stop_keys:
        m2 = re.search(e, texto[start:], flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if m2:
            stop = start + m2.start()
            stop_pat_used = e
            break

    bloque = texto[start:stop].strip()
    context = texto[max(0, start - window_chars):min(len(texto), start + window_chars)]

    print(f"Start pattern usado: {start_pat_used}")
    print(f"Stop pattern usado: {stop_pat_used or '(fin del texto)'}")
    print(f"Tamaño bloque extraído: {len(bloque)} chars")
    print("Contexto alrededor del inicio (±200 chars):")
    print("---")
    print(context)
    print("---\n")
    return bloque


# ---------------------------
# MAIN
# ---------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python debug_pdf_extraccion.py \"ruta\\al\\Proyecto Ayto Carrascal.pdf\"")
        sys.exit(1)

    path_pdf = sys.argv[1]
    base = os.path.splitext(path_pdf)[0]

    print("Leyendo con pdfplumber…")
    raw = leer_pdf(path_pdf)
    with open(base + ".raw.txt", "w", encoding="utf-8") as f:
        f.write(raw)
    print(f"✅ Guardado RAW: {os.path.basename(base)}.raw.txt (len={len(raw)})")

    cleaned = limpiar_texto_basico(raw)
    with open(base + ".cleaned.txt", "w", encoding="utf-8") as f:
        f.write(cleaned)
    print(f"✅ Guardado CLEANED: {os.path.basename(base)}.cleaned.txt (len={len(cleaned)})")

    no_index = quitar_lineas_indice(cleaned)
    with open(base + ".noindex.txt", "w", encoding="utf-8") as f:
        f.write(no_index)
    print(f"✅ Guardado NOINDEX: {os.path.basename(base)}.noindex.txt (len={len(no_index)})")

    # ---------------------------
    # NUEVA EXTRACCIÓN AJUSTADA
    # ---------------------------
    print("\n=== EXTRACCIÓN REFINADA DE INTRODUCCIÓN (pasada 1) ===")
    intro1 = cortar_bloque_flexible(
        no_index,
        start_keys=[
            r"(?m)^\s*1[.,]?\s*1\b.*Antecedentes",
            r"(?m)^\s*1[.,]?\s*Introducci[oó]n\b",
            r"(?m)^\s*Cap[ií]tulo\s*1\b.*Introducci[oó]n",
        ],
        stop_keys=[
            r"(?m)^\s*1[.,]?\s*2\b",
            r"(?m)^\s*Objeto\b",
            r"(?m)^\s*1[.,]?\s*2[^\d]?",
            r"(?m)^\s*2[.,]?\s*0?\b",
            r"(?m)^\s*GEOLOG[ÍI]A\b",
            r"(?m)^\s*Geolog[ií]a\b",
            r"(?m)^\s*Situaci[oó]n\b",
            r"(?m)^\s*Emplazamiento\b",
        ],
        window_chars=200
    )

    if len(intro1) < 400:
        print("\n⚠️  Bloque corto; intentamos cortar tras el Índice y repetir…")
        after_index = cortar_despues_del_indice(no_index)
        with open(base + ".after_index.txt", "w", encoding="utf-8") as f:
            f.write(after_index)
        print(f"✅ Guardado AFTER_INDEX: {os.path.basename(base)}.after_index.txt (len={len(after_index)})")

        print("\n=== EXTRACCIÓN REFINADA DE INTRODUCCIÓN (pasada 2) ===")
        intro2 = cortar_bloque_flexible(
            after_index,
            start_keys=[
                r"(?m)^\s*1[.,]?\s*1\b.*Antecedentes",
                r"(?m)^\s*1[.,]?\s*Introducci[oó]n\b",
                r"(?m)^\s*Cap[ií]tulo\s*1\b.*Introducci[oó]n",
            ],
            stop_keys=[
                r"(?m)^\s*1[.,]?\s*2\b",
                r"(?m)^\s*Objeto\b",
                r"(?m)^\s*1[.,]?\s*2[^\d]?",
                r"(?m)^\s*2[.,]?\s*0?\b",
                r"(?m)^\s*GEOLOG[ÍI]A\b",
                r"(?m)^\s*Geolog[ií]a\b",
                r"(?m)^\s*Situaci[oó]n\b",
                r"(?m)^\s*Emplazamiento\b",
            ],
            window_chars=200
        )
        intro_final = intro2
    else:
        intro_final = intro1

    # ---------------------------
    # GUARDAR RESULTADOS
    # ---------------------------
    with open(base + ".introduccion_refinada.txt", "w", encoding="utf-8") as f:
        f.write(intro_final or "")
    print(f"\n✅ Guardado INTRO REFINADA: {os.path.basename(base)}.introduccion_refinada.txt (len={len(intro_final)})")

    print("\n=== RESUMEN ===")
    print(f"- RAW:         {len(raw)} chars")
    print(f"- CLEANED:     {len(cleaned)} chars")
    print(f"- NOINDEX:     {len(no_index)} chars")
    print(f"- INTRO FINAL: {len(intro_final)} chars")
    if len(intro_final) < 400:
        print("⚠️  Sigue saliendo corto. Revisa *.noindex.txt y *.after_index.txt para ajustar los patrones.")
