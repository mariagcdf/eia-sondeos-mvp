# app.py
import os
from pathlib import Path
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv

# Importa las funciones nuevas
from extraccion_info_proyecto import extract_from_project_and_eia
from core.export_docx_template import export_docx_from_placeholder_map

load_dotenv(override=True)
st.set_page_config(page_title="EIA (Sondeo nuevo)", page_icon="🧭", layout="centered")

st.title("🧭 Generador de EIA — Sondeo nuevo (principal)")
st.caption(
    "Se extraen los datos del proyecto y se genera el DOCX con una sola tabla "
    "para el sondeo nuevo. Si se detecta un sondeo existente, se insertará un aviso."
)

pdf = st.file_uploader("Sube el PROYECTO en PDF", type=["pdf"])

if not pdf:
    st.info("Sube un PDF para comenzar.")
else:
    with st.spinner("Extrayendo información…"):
        try:
            datos_min, placeholders = extract_from_project_and_eia(pdf)
            st.success("✅ Extracción completada.")
        except Exception as e:
            st.error("❌ Error al procesar el PDF.")
            st.error(f"Detalle técnico: {e}")
            st.stop()

    # ===== Mostrar resumen =====
    st.subheader("Vista previa de datos extraídos")
    st.json(placeholders)

    # ===== Exportar =====
    st.subheader("Exportar documento Word")

    hoy = datetime.now().strftime("%Y%m%d")
    base = f"EIA_simplificada_{hoy}".replace(" ", "_")
    out_dir = Path("outputs")
    out_dir.mkdir(exist_ok=True)
    docx_path = out_dir / f"{base}.docx"

    with st.spinner("Generando DOCX..."):
        saved = export_docx_from_placeholder_map(
            placeholder_map=placeholders,
            plantilla_path="plantilla_EIA.docx",
            out_path=str(docx_path),
        )

    with open(saved, "rb") as f:
        st.download_button(
            "⬇️ Descargar DOCX",
            data=f,
            file_name=f"{base}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
