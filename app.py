# app.py
import os
from pathlib import Path
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv
import json
import subprocess

from core.extraccion.regex_extract import regex_extract_min_fields
from core.build_global_json import build_global_placeholders
from core.export_docx_template import export_docx_from_placeholder_map
from core.extraccion.pdf_reader import leer_pdf_texto_completo
from core.sintesis.instalacion_electrica import redactar_instalacion_llm


# ========================
# CONFIGURACIÓN INICIAL
# ========================
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

st.set_page_config(
    page_title="EIA (Sondeo nuevo)",
    page_icon="🧭",
    layout="centered"
)

st.title("🧭 Generador de EIA — Sondeo nuevo")
st.caption("Flujo controlado: subir PDF → elegir tipo de instalación → comprobar Red Natura → exportar DOCX")


# ========================
# SUBIR PDF
# ========================
pdf = st.file_uploader("📄 Sube el PROYECTO en PDF", type=["pdf"])

if pdf and "json_path" not in st.session_state:
    with st.spinner("🔍 Procesando el documento..."):
        texto_completo = leer_pdf_texto_completo(pdf)
        datos_regex = regex_extract_min_fields(texto_completo)

        out_dir = Path("outputs")
        out_dir.mkdir(exist_ok=True)
        json_path = out_dir / f"placeholders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        placeholders = build_global_placeholders(
            texto_relevante=texto_completo,
            texto_completo_pdf=texto_completo,
            datos_regex_min=datos_regex,
            save_to=str(json_path)
        )

        st.success("✅ PDF procesado correctamente.")
        st.caption(f"📁 JSON generado: `{json_path.name}`")

        st.session_state["json_path"] = str(json_path)
        st.session_state["pdf_cargado"] = True

elif "json_path" in st.session_state:
    st.info(f"📄 Archivo ya procesado: {Path(st.session_state['json_path']).name}")

else:
    st.stop()


# ========================
# SELECCIÓN DE TIPO ELÉCTRICO
# ========================
st.markdown("---")
st.subheader("⚡ Tipo de instalación eléctrica")

st.write("Selecciona el tipo de alimentación prevista para el sondeo:")

col1, col2 = st.columns(2)
seleccion = None

with col1:
    if st.button("🔌 Conexión a red eléctrica"):
        seleccion = "red"

with col2:
    if st.button("☀️ Instalación fotovoltaica"):
        seleccion = "fotovoltaica"

# Si se ha pulsado uno de los dos botones
if seleccion:
    json_path = Path(st.session_state["json_path"])
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    tipo_anterior = st.session_state.get("ultimo_tipo")

    # Solo regenera si ha cambiado
    if tipo_anterior != seleccion:
        with st.spinner(f"⚙️ Generando texto técnico para instalación {seleccion}..."):
            nuevo_texto = redactar_instalacion_llm(data, tipo=seleccion)
            data["instalacion_electrica"] = nuevo_texto

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            st.session_state["ultimo_tipo"] = seleccion

        st.success(f"✅ Texto actualizado: instalación {seleccion}.")
    else:
        st.info("ℹ️ Ya está generada esta opción.")

    # Vista previa del texto generado
    texto_actual = data.get("instalacion_electrica", "")
    if texto_actual:
        st.text_area("Vista previa del texto generado:", texto_actual, height=150)

# ========================
# 🌿 COMPROBAR RED NATURA 2000
# ========================

def comprobar_red_natura(json_path: Path) -> bool:
    """
    Llama al script export_info_red_natura.py para verificar si las coordenadas
    del proyecto están dentro de un espacio Red Natura 2000.
    Devuelve True si hay coincidencia, False en caso contrario.
    """
    try:
        result = subprocess.run(
            ["python", "core/sintesis/export_info_red_natura.py", str(json_path)],
            capture_output=True, text=True, timeout=120
        )

        # Mostrar salida de depuración
        st.text_area("🧩 Log Red Natura:", result.stdout, height=150)

        if "✅" in result.stdout or "DENTRO" in result.stdout.upper():
            return True
        return False
    except Exception as e:
        st.warning(f"⚠️ Error al comprobar Red Natura: {e}")
        return False


if "json_path" in st.session_state and "ultimo_tipo" in st.session_state:
    json_path = Path(st.session_state["json_path"])

    st.markdown("---")
    st.subheader("🌿 Comprobación ambiental")

    if st.button("🔎 Comprobar si el proyecto está dentro de Red Natura 2000"):
        with st.spinner("🌍 Analizando coordenadas y consultando Red Natura 2000..."):
            en_red_natura = comprobar_red_natura(json_path)

            # Cargar datos actuales
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if en_red_natura:
                st.success("✅ El proyecto se encuentra dentro de un espacio Red Natura 2000.")
                data["red_natura"] = True
            else:
                st.warning("⚠️ El proyecto NO está dentro de Red Natura 2000.")
                data["red_natura"] = False
                st.info("🪶 Generando texto alternativo de medio biótico...")

                try:
                    subprocess.run(
                        ["python", "core/sintesis/medio_biotico_no_red_natura.py", str(json_path)],
                        check=True
                    )
                    st.success("🪶 Texto alternativo de medio biótico generado correctamente.")
                except subprocess.CalledProcessError as e:
                    st.error(f"❌ Error al generar texto alternativo: {e}")

            # Guardar estado actualizado en el JSON
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    # 👀 Vista previa del texto de medio biótico si existe
    with open(st.session_state["json_path"], "r", encoding="utf-8") as f:
        data_actual = json.load(f)

    texto_medio_biotico = data_actual.get("medio_biotico", "")
    if texto_medio_biotico:
        st.text_area("🌱 Vista previa del texto de medio biótico:", texto_medio_biotico, height=250)

# ========================
# EXPORTAR DOCX FINAL
# ========================
st.markdown("---")
st.subheader("🧾 Exportar documento final")

if "json_path" in st.session_state:
    with open(st.session_state["json_path"], "r", encoding="utf-8") as f:
        placeholders_final = json.load(f)

    hoy = datetime.now().strftime("%Y%m%d")
    base = f"EIA_simplificada_{hoy}"
    docx_path = Path("outputs") / f"{base}.docx"

    if st.button("💾 Generar DOCX final"):
        # 🔄 Asegurar lectura del JSON más reciente antes de nada
        with open(st.session_state["json_path"], "r", encoding="utf-8") as f:
            placeholders_final = json.load(f)

        # 🧠 Procesar redacción automática de placeholders ANTES de exportar
        with st.spinner("🧠 Procesando formato y redacción técnica..."):
            try:
                subprocess.run(
                    ["python", "core/sintesis/redactar_placeholder.py"],
                    check=True,
                    capture_output=True,
                    text=True
                )
                st.success("✅ Formato y redacción técnica completados correctamente.")
            except subprocess.CalledProcessError as e:
                st.warning("⚠️ Error durante la redacción automática de placeholders.")
                st.text(e.stdout or "")
                st.text(e.stderr or "")

        # 📥 Volvemos a abrir el JSON actualizado (ya modificado por IA)
        with open(st.session_state["json_path"], "r", encoding="utf-8") as f:
            placeholders_final = json.load(f)

        # 📄 Exportación final a Word
        with st.spinner("📄 Generando documento Word final..."):
            export_docx_from_placeholder_map(
                placeholder_map=placeholders_final,
                plantilla_path="plantilla_EIA.docx",
                out_path=str(docx_path)
            )

        # 💾 Botón de descarga
        with open(docx_path, "rb") as f:
            st.download_button(
                "⬇️ Descargar DOCX generado",
                data=f,
                file_name=f"{base}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
