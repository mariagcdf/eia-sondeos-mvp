# app.py
import os
from pathlib import Path
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv

from extraccion_info_proyecto import (
    extract_from_project_and_eia,
    export_eia_docx
)

load_dotenv(override=True)
st.set_page_config(page_title="EIA (Sondeo nuevo)", page_icon="🧭", layout="centered")

st.title("🧭 Generador de EIA — Sondeo nuevo (principal)")
st.caption("Se extraen los datos del proyecto y se genera el DOCX con una sola tabla para el sondeo nuevo. Si se detecta un sondeo existente, se insertará un aviso.")

pdf = st.file_uploader("Sube el PROYECTO en PDF", type=["pdf"])

if not pdf:
    st.info("Sube un PDF para comenzar.")
else:
    with st.spinner("Extrayendo información…"):
        try:
            datos_min, literal_blocks, html = extract_from_project_and_eia(pdf)
            st.success("✅ Extracción completada.")
        except Exception as e:
            st.error("❌ Error al procesar el PDF.")
            st.error(f"Detalle técnico: {e}")
            st.stop()

    flags = datos_min.get("flags") or {}
    if flags.get("hay_sondeo_existente"):
        st.warning("Se ha detectado un **sondeo EXISTENTE** en el documento. En el DOCX aparecerá un aviso para que copies esa parte manualmente.")

    # ===== Editor manual mínimo =====
    st.subheader("Revisar y corregir datos del sondeo **principal**")
    p = datos_min.get("parametros", {}) or {}
    c = (datos_min.get("coordenadas") or {})
    utm = (c.get("utm") or {})
    geo = (c.get("geo") or {})

    with st.form("edicion"):
        col1, col2 = st.columns(2)
        with col1:
            prof_m = st.number_input("Profundidad proyectada (m)", value=float(p.get("profundidad_proyectada_m") or 0.0), step=1.0)
            d_ini  = st.number_input("Ø perforación INICIAL (mm)", value=float(p.get("diametro_perforacion_inicial_mm") or 0.0), step=1.0)
            d_def  = st.number_input("Ø perforación DEFINITIVO (mm)", value=float(p.get("diametro_perforacion_definitivo_mm") or 0.0), step=1.0)
            d_imp  = st.number_input("Ø tubería de impulsión (mm)", value=float(p.get("diametro_tuberia_impulsion_mm") or 0.0), step=0.1)
        with col2:
            qmax  = st.number_input("Caudal máximo instantáneo (L/s)", value=float(p.get("caudal_max_instantaneo_l_s") or 0.0), step=0.01)
            qmin  = st.number_input("Caudal mínimo (L/s)", value=float(p.get("caudal_minimo_l_s") or 0.0), step=0.01)
            kw    = st.number_input("Potencia de la bomba (kW)", value=float(p.get("potencia_bombeo_kw") or 0.0), step=0.1)

        colp1, colp2, colp3 = st.columns(3)
        def _as_str(v): return "" if v is None else str(v)
        with colp1:
            utm_x = st.text_input("UTM X (principal)", _as_str(utm.get("x")))
            lat   = st.text_input("Latitud (principal)", _as_str(geo.get("lat")))
        with colp2:
            utm_y = st.text_input("UTM Y (principal)", _as_str(utm.get("y")))
            lon   = st.text_input("Longitud (principal)", _as_str(geo.get("lon")))
        with colp3:
            huso  = st.text_input("Huso (principal)", _as_str(utm.get("huso") or "30"))
            datum = st.text_input("Datum (principal)", _as_str(utm.get("datum") or "ETRS-89"))

        aplicar = st.form_submit_button("Aplicar cambios")
        if aplicar:
            def _num_safe(s):
                if s is None or s == "": return None
                s = s.replace(".", "").replace(",", ".")
                try: return float(s)
                except: return None

            datos_min.setdefault("parametros", {}).update({
                "profundidad_proyectada_m": prof_m or None,
                "diametro_perforacion_inicial_mm": d_ini or None,
                "diametro_perforacion_definitivo_mm": d_def or None,
                "diametro_tuberia_impulsion_mm": d_imp or None,
                "caudal_max_instantaneo_l_s": qmax or None,
                "caudal_minimo_l_s": qmin or None,
                "potencia_bombeo_kw": kw or None,
            })
            datos_min.setdefault("coordenadas", {}).setdefault("utm", {})
            datos_min["coordenadas"].setdefault("geo", {})
            datos_min["coordenadas"]["utm"].update({
                "x": _num_safe(utm_x),
                "y": _num_safe(utm_y),
                "huso": huso or None,
                "datum": datum or None,
            })
            datos_min["coordenadas"]["geo"].update({
                "lat": lat or None,
                "lon": lon or None,
            })
            st.success("Cambios aplicados.")

    # ===== Exportar =====
    st.subheader("Exportar")
    hoy = datetime.now().strftime("%Y%m%d")
    base = f"EIA_simplificada_{hoy}".replace(" ", "_")
    out_dir = Path("outputs"); out_dir.mkdir(exist_ok=True)
    docx_path = out_dir / f"{base}.docx"

    saved = export_eia_docx(datos_min, literal_blocks, str(docx_path))
    with open(saved, "rb") as f:
        st.download_button(
            "⬇️ Descargar DOCX",
            data=f,
            file_name=f"{base}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
