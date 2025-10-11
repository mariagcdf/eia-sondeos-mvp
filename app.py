# app.py
import os
from pathlib import Path
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv

from core.extraccion.regex_extract import regex_extract_min_fields
from core.build_global_json import build_global_placeholders
from core.export_docx_template import export_docx_from_placeholder_map
from core.extraccion.pdf_reader import leer_pdf_texto_completo

# ========================
# CONFIGURACIÓN INICIAL
# ========================
load_dotenv(override=True)
st.set_page_config(
    page_title="EIA (Sondeo nuevo)",
    page_icon="🧭",
    layout="centered"
)

st.title("🧭 Generador de EIA — Sondeo nuevo (flujo limpio)")
st.caption("Versión actualizada sin placeholders antiguos ni claves obsoletas (PH_situacion, tabla_coordenadas, etc.)")

# ========================
# SUBIR PDF
# ========================
pdf = st.file_uploader("📄 Sube el PROYECTO en PDF", type=["pdf"])

if not pdf:
    st.info("Sube un PDF para comenzar.")
else:
    with st.spinner("🔍 Extrayendo información del documento..."):
        # 1️⃣ Leer texto completo
        texto_completo = leer_pdf_texto_completo(pdf)

        # 2️⃣ Extraer datos numéricos y de coordenadas
        datos_regex = regex_extract_min_fields(texto_completo)

        # 3️⃣ Construir placeholders unificados
        out_dir = Path("outputs"); out_dir.mkdir(exist_ok=True)
        json_path = out_dir / f"placeholders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        placeholders = build_global_placeholders(
            texto_relevante=texto_completo,
            texto_completo_pdf=texto_completo,
            datos_regex_min=datos_regex,
            save_to=str(json_path)  # guarda el JSON automáticamente
        )

        st.success("✅ Extracción completada correctamente.")
        st.caption(f"📁 Placeholders guardados en `{json_path}`")

    # ========================
    # EXPORTAR DOCX
    # ========================
    st.subheader("🧾 Exportar EIA en formato Word")

    hoy = datetime.now().strftime("%Y%m%d")
    base = f"EIA_simplificada_{hoy}".replace(" ", "_")
    docx_path = out_dir / f"{base}.docx"

    export_docx_from_placeholder_map(
        placeholder_map=placeholders,
        plantilla_path="plantilla_EIA.docx",
        out_path=str(docx_path)
    )

    with open(docx_path, "rb") as f:
        st.download_button(
            "⬇️ Descargar DOCX generado",
            data=f,
            file_name=f"{base}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    st.caption("💾 Se han eliminado los placeholders obsoletos y se respetan los saltos de párrafo.")
