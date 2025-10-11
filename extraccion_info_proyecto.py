from typing import Dict, Any, Tuple
from core.extraccion.pdf_reader import leer_pdf_texto_completo
from core.extraccion.regex_extract import regex_extract_min_fields
from core.build_global_json import build_global_placeholders


def extract_from_project_and_eia(uploaded_file, model="gpt-4.1-mini") -> Tuple[Dict[str, Any], Dict[str, str]]:
    """
    Devuelve:
      - datos_min: salida mínima por regex
      - placeholders: JSON global generado por build_global_placeholders
    """
    # 1️⃣ Leer texto completo del PDF
    try:
        texto_completo = leer_pdf_texto_completo(uploaded_file)
    except Exception:
        texto_completo = ""

    # 2️⃣ Extraer datos básicos por regex
    try:
        datos_regex = regex_extract_min_fields(texto_completo)
    except Exception:
        datos_regex = {}

    # 3️⃣ Construir JSON global de placeholders (usando build_global_json.py)
    placeholders = build_global_placeholders(
        texto_relevante=texto_completo,
        texto_completo_pdf=texto_completo,
        datos_regex_min=datos_regex,
        model=model
    )

    return datos_regex, placeholders
