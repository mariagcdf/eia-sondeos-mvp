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
# 👉 Para generar el texto técnico de instalación eléctrica con IA
from core import llm_utils

# ================== Configuración e inicio ==================
load_dotenv(override=True)
st.set_page_config(page_title="EIA Simplificada", page_icon="🧭", layout="centered")

# --- Estilos globales (modo oscuro + tipografías más legibles) ---
st.markdown("""
<style>
:root {
  --brand:#1e88e5;
  --ink:#e8f0fe;
  --ink-soft:#b3c6ff;
}
html, body, [class*="css"]  { color: #f5f7fb !important; }
section.main>div { max-width: 1000px; }
h1,h2,h3 { letter-spacing: .2px; }
.badge {
  display:inline-block; padding:4px 10px; border:1px solid #3d4a5e; border-radius:999px;
  font-size:12px; color:#dfe6f3; background:rgba(255,255,255,.04); margin-left:8px;
}
.card {
  border:1px solid #2e384a; border-radius:12px; padding:16px 18px; background:rgba(19,25,36,.55);
}
.btn-row > div { display:inline-block; margin-right:10px; }
.small-note { color:#a9b7d0; font-size:12px; }
table { color: #f5f7fb !important; }
</style>
""", unsafe_allow_html=True)

# ================== Encabezado ==================
st.title("🧭 Generador de EIA (a partir del PROYECTO)")
st.caption("Automatiza la preparación del **Documento Ambiental Simplificado** a partir del proyecto en PDF, combinando extracción por *regex* (datos numéricos) e IA (texto).")

# ================== Sidebar ==================
with st.sidebar:
    st.markdown("### ⚙️ Ajustes")
    api_prefix = (os.getenv("OPENAI_API_KEY") or "")[:10]
    st.write(f"**API Key detectada:** {api_prefix + '…' if api_prefix else '— no cargada —'}")
    modelo = st.selectbox(
        "Modelo para IA (solo para textos complejos):",
        ["gpt-4.1-mini", "gpt-4o-mini"],
        index=0
    )
    st.markdown("---")
    st.markdown("### ℹ️ Cómo funciona")
    st.markdown(
        "- Carga el **PROYECTO en PDF**.\n"
        "- El sistema extrae datos con *regex* e IA.\n"
        "- Revisa/edita los campos y **descarga** el HTML o DOCX basado en tu plantilla."
    )
    st.markdown("---")
    st.markdown(
        "<span class='small-note'>Consejo: si el documento usa separadores de miles (p. ej. 4.516.789), el sistema los limpia automáticamente.</span>",
        unsafe_allow_html=True
    )

# ================== Carga de archivo ==================
pdf = st.file_uploader("Sube el **PROYECTO** en PDF", type=["pdf"], help="Tamaño máximo 200 MB.")

if not pdf:
    st.markdown("<div class='card'>Carga un PDF para comenzar.</div>", unsafe_allow_html=True)

# ================== Procesado ==================
if pdf:
    with st.spinner("Procesando el PDF y extrayendo información…"):
        try:
            # 👇 AHORA DEVUELVE 4 VALORES
            datos_min, literal_blocks, usadas, html = extract_from_project_and_eia(
                pdf, eia_docx=None, model=modelo
            )
            st.success("✅ Extracción completada.")
        except Exception as e:
            st.error("❌ Error al procesar el PDF.")
            st.error(f"Detalle técnico: {e}")
            st.stop()

    st.success("Listo. Revisa, ajusta lo necesario y exporta tu EIA.")

    # Muestra opcional de páginas usadas
    if usadas:
        st.markdown(f"<div class='small-note'>Páginas usadas para la vista IA: {', '.join(map(str, usadas))}</div>", unsafe_allow_html=True)

    # ================== Datos clave (previa) ==================
    st.subheader("1) Datos clave extraídos")
    st.markdown("Puedes revisarlos y ajustarlos en el editor de abajo antes de exportar.")
    st.json(datos_min)

    # ================== Editor manual ==================
    st.subheader("2) Revisar y corregir datos (opcional)")
    with st.form("edicion_manual"):
        p = datos_min.get("parametros", {}) or {}
        l = datos_min.get("localizacion", {}) or {}
        utm = (datos_min.get("coordenadas", {}) or {}).get("utm", {}) or {}

        col1, col2 = st.columns(2)
        with col1:
            poligono = st.text_input("Polígono", str(l.get("poligono") or ""))
            parcela = st.text_input("Parcela", str(l.get("parcela") or ""))
            refcat = st.text_input("Referencia catastral", str(l.get("referencia_catastral") or ""))

            prof_m = st.number_input("Profundidad proyectada (m)", value=float(p.get("profundidad_proyectada_m") or 0.0), step=1.0)
            d_ini  = st.number_input("Ø perforación INICIAL (mm)", value=float(p.get("diametro_perforacion_inicial_mm") or 0.0), step=1.0)
            d_def  = st.number_input("Ø perforación DEFINITIVO / entubación (mm)", value=float(p.get("diametro_perforacion_definitivo_mm") or 0.0), step=1.0)

        with col2:
            utm_x = st.text_input("UTM X", str(utm.get("x") or ""))
            utm_y = st.text_input("UTM Y", str(utm.get("y") or ""))
            huso  = st.text_input("Huso", str(utm.get("huso") or "30"))
            datum = st.text_input("Datum", str(utm.get("datum") or "ETRS-89"))

            d_imp = st.number_input("Ø tubería de impulsión (mm)", value=float(p.get("diametro_tuberia_impulsion_mm") or 0.0), step=0.1)
            qmax  = st.number_input("Caudal máximo instantáneo (L/s)", value=float(p.get("caudal_max_instantaneo_l_s") or 0.0), step=0.01)
            qmin  = st.number_input("Caudal mínimo (L/s)", value=float(p.get("caudal_minimo_l_s") or 0.0), step=0.01)
            kw    = st.number_input("Potencia de la bomba (kW)", value=float(p.get("potencia_bombeo_kw") or 0.0), step=0.1)

        aplicado = st.form_submit_button("Aplicar cambios")
        if aplicado:
            datos_min.setdefault("parametros", {})
            datos_min.setdefault("localizacion", {})
            datos_min.setdefault("coordenadas", {}).setdefault("utm", {})

            datos_min["localizacion"]["poligono"] = poligono or None
            datos_min["localizacion"]["parcela"] = parcela or None
            datos_min["localizacion"]["referencia_catastral"] = refcat or None

            # UTM con saneo decimal
            def _num_safe(s):
                if not s: return None
                s = s.replace(".", "").replace(",", ".")
                try:
                    return float(s)
                except:
                    return None
            datos_min["coordenadas"]["utm"]["x"] = _num_safe(utm_x)
            datos_min["coordenadas"]["utm"]["y"] = _num_safe(utm_y)
            datos_min["coordenadas"]["utm"]["huso"] = huso or None
            datos_min["coordenadas"]["utm"]["datum"] = datum or None

            datos_min["parametros"]["profundidad_proyectada_m"] = prof_m or None
            datos_min["parametros"]["diametro_perforacion_inicial_mm"] = d_ini or None
            datos_min["parametros"]["diametro_perforacion_definitivo_mm"] = d_def or None
            datos_min["parametros"]["diametro_tuberia_impulsion_mm"] = d_imp or None
            datos_min["parametros"]["caudal_max_instantaneo_l_s"] = qmax or None
            datos_min["parametros"]["caudal_minimo_l_s"] = qmin or None
            datos_min["parametros"]["potencia_bombeo_kw"] = kw or None

            st.success("Cambios aplicados correctamente.")

    # ================== Instalación eléctrica (selector + IA + editor) ==================
    st.subheader("3) Instalación eléctrica")
    colA, colB = st.columns([1, 2])

    with colA:
        opcion_ie = st.radio(
            "Modalidad de alimentación",
            options=["Conexión a red", "Paneles fotovoltaicos"],
            index=0,
            help="Elige si la bomba se alimentará desde la red de baja tensión existente o con un sistema fotovoltaico autónomo."
        )
        generar = st.button("✨ Generar texto técnico (IA)")

    # Estado para texto generado
    if "ie_texto" not in st.session_state:
        st.session_state.ie_texto = ""

    if generar:
        try:
            modo = "red" if opcion_ie == "Conexión a red" else "fotovoltaica"
            gen_txt = llm_utils.generar_instalacion_electrica_texto(modo, datos_min, model=modelo)
            st.session_state.ie_texto = gen_txt
            st.success("Texto generado.")
        except Exception as e:
            st.error(f"No se pudo generar el texto: {e}")

    with colB:
        texto_ie = st.text_area(
            "Texto de la sección «Instalación eléctrica» (editable):",
            value=st.session_state.ie_texto,
            height=160,
            placeholder="Pulsa '✨ Generar texto técnico (IA)' o escribe aquí tu texto…"
        )

    # Inserta el bloque en literal_blocks antes de exportar
    try:
        literal_blocks["instalacion_electrica"] = texto_ie or ""
    except Exception:
        pass

    # ================== Descargas ==================
    st.subheader("4) Exportar")
    hoy = datetime.now().strftime("%Y%m%d")
    muni = (datos_min.get("localizacion") or {}).get("municipio") or "Proyecto"
    base_name = f"EIA_simplificada_{muni}_{hoy}".replace(" ", "_")

    # HTML
    st.download_button(
        "⬇️ Descargar HTML",
        data=html,
        file_name=f"{base_name}.html",
        mime="text/html",
        help="Exporta una versión web del documento."
    )

    # DOCX (usa tu plantilla con placeholders {{...}})
    out_dir = Path("outputs"); out_dir.mkdir(exist_ok=True)
    docx_path = out_dir / f"{base_name}.docx"
    saved = export_eia_docx(datos_min, literal_blocks, str(docx_path))
    with open(saved, "rb") as f:
        st.download_button(
            "⬇️ Descargar DOCX",
            data=f,
            file_name=f"{base_name}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            help="Exporta la versión editable en Word basada en tu plantilla."
        )

    st.markdown("<div class='badge'>Listo para revisión</div>", unsafe_allow_html=True)
