# app.py
import os
import sys
from pathlib import Path
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv
import json
import subprocess
from subprocess import Popen, PIPE, STDOUT
import time
from typing import Optional

# Raíz del proyecto
PROJECT_ROOT = Path(__file__).resolve().parent

# --- imports del proyecto ---
from core.extraccion.regex_extract import regex_extract_min_fields
from core.build_global_json import build_global_placeholders
from core.export_docx_template import export_docx_from_placeholder_map
from core.extraccion.pdf_reader import leer_pdf_texto_completo
from core.sintesis.instalacion_electrica import redactar_instalacion_llm

# ========================
# CONFIGURACIÓN INICIAL
# ========================
env_path = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=env_path, override=True)

st.set_page_config(page_title="EIA (Sondeo nuevo)", page_icon="🧭", layout="centered")
st.title("🧭 Generador de EIA — Sondeo nuevo")
st.caption("Flujo: subir PDF → extracción/redacción → Red Natura 2000 → medio biótico → exportar DOCX")

# ========================
# HELPERS
# ========================
def run_script_streaming(cmd: list[str], ui_title: str, height: int = 240) -> str:
    """Ejecuta un script mostrando logs en vivo en Streamlit."""
    log_placeholder = st.empty()
    acc = []
    env = {**os.environ, "PYTHONUNBUFFERED": "1"}

    log_placeholder.markdown(f"**{ui_title}**")
    with st.spinner("Ejecutando..."):
        try:
            proc = Popen(cmd, stdout=PIPE, stderr=STDOUT, text=True, bufsize=1, cwd=str(PROJECT_ROOT), env=env)
            for line in iter(proc.stdout.readline, ''):
                acc.append(line.rstrip())
                log_placeholder.text_area(ui_title, "\n".join(acc[-60:]), height=height)
            proc.stdout.close()
            proc.wait()
        except Exception as e:
            acc.append(f"[ERROR] {e}")
            log_placeholder.text_area(ui_title, "\n".join(acc[-60:]), height=height)
    return "\n".join(acc)


def load_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def update_json_field(json_path: Path, updates: dict):
    """Actualiza campos indicados en un JSON existente."""
    try:
        data = load_json(json_path)
        data.update({k: v for k, v in updates.items() if v not in (None, "", [])})
        save_json(json_path, data)
        st.info(f"🗂️ JSON actualizado: {', '.join(updates.keys())}")
    except Exception as e:
        st.error(f"❌ Error actualizando JSON: {e}")


def comprobar_red_natura(json_path: Path) -> bool:
    """Ejecuta la comprobación Red Natura y devuelve True/False."""
    cmd = [sys.executable, "-u", "core/export_info_red_natura.py", str(json_path)]
    run_script_streaming(cmd, ui_title="🧩 Log Red Natura", height=240)
    data = load_json(json_path)
    estado = (data.get("estado_red_natura") or "").lower()
    return (estado == "en_red_natura") or bool(data.get("red_natura"))


def find_script(*paths: str) -> str:
    """Busca el primer script existente entre varias rutas posibles."""
    for p in paths:
        candidate = Path(p)
        if candidate.exists():
            return str(candidate)
    raise FileNotFoundError(f"No se encontró ninguno de los scripts: {paths}")

def get_latest_json(output_dir: str = "outputs") -> Optional[Path]:
    """Devuelve el JSON más reciente en outputs/."""
    out_dir = Path(output_dir)
    json_files = sorted(out_dir.glob("placeholders_*.json"), key=os.path.getmtime, reverse=True)
    return json_files[0] if json_files else None

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

        build_global_placeholders(
            texto_relevante=texto_completo,
            texto_completo_pdf=texto_completo,
            datos_regex_min=datos_regex,
            save_to=str(json_path)
        )

        st.success("✅ PDF procesado correctamente.")
        st.caption(f"📁 JSON generado: `{json_path.name}`")

        st.session_state["json_path"] = str(json_path)
        st.session_state["pdf_cargado"] = True
        st.session_state["rn_done"] = False

elif "json_path" in st.session_state:
    st.info(f"📄 Archivo ya procesado: {Path(st.session_state['json_path']).name}")
else:
    st.stop()

json_path = Path(st.session_state["json_path"])


# ========================
# ⚡ INSTALACIÓN ELÉCTRICA
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

if seleccion:
    data = load_json(json_path)
    tipo_anterior = st.session_state.get("ultimo_tipo")

    if tipo_anterior != seleccion:
        with st.spinner(f"⚙️ Generando texto técnico para instalación {seleccion}..."):
            nuevo_texto = redactar_instalacion_llm(data, tipo=seleccion)
            update_json_field(json_path, {"instalacion_electrica": nuevo_texto})
            st.session_state["ultimo_tipo"] = seleccion
        st.success(f"✅ Texto actualizado: instalación {seleccion}.")
    else:
        st.info("ℹ️ Ya está generada esta opción.")

    texto_actual = load_json(json_path).get("instalacion_electrica", "")
    if texto_actual:
        st.text_area("Vista previa del texto generado:", texto_actual, height=150)


# ========================
# 🏠 INFORMACIÓN CATASTRAL
# ========================
st.markdown("## 🏠 Información catastral")

if json_path.exists():
    st.write(f"📄 Archivo en uso: `{json_path.name}`")

    boton_catastro = st.button("🧭 Obtener información catastral automáticamente")

    if boton_catastro:
        with st.spinner("Consultando visor CH Duero y extrayendo información del Catastro..."):
            script_catastro_path = find_script("core/sintesis/catastro_client.py")
            cmd = [sys.executable, "-u", script_catastro_path, str(json_path)]
            run_script_streaming(
                cmd,
                ui_title="🏠 Proceso de extracción de información catastral",
                height=300
            )

        # 🔄 Recargar JSON actualizado tras la ejecución
        data_prev = load_json(json_path)
        update_json_field(json_path, {
            "catastro_structured": data_prev.get("catastro_structured", "")
        })

        # ✅ Mensaje de confirmación
        if data_prev.get("catastro_structured"):
            st.success("✅ Información catastral extraída y guardada correctamente.")
        else:
            st.warning("⚠️ No se encontró información catastral (puede que el visor no haya devuelto datos).")

else:
    st.warning("⚠️ No se encontró el archivo JSON cargado.")


# ========================
# 🌿 COMPROBACIÓN AMBIENTAL
# ========================
st.markdown("---")
st.subheader("🌿 Comprobación ambiental (Red Natura 2000)")

if st.button("🔎 Comprobar Red Natura y generar medio biótico si procede"):
    with st.spinner("Consultando visor y actualizando JSON…"):
        dentro = comprobar_red_natura(json_path)

    if dentro:
        st.success("✅ Dentro de Red Natura 2000. Generando medio biótico específico…")
        try:
            run_script_streaming(
                [sys.executable, "-u", "core/sintesis/medio_biotico_red_natura.py", str(json_path)],
                ui_title="🪶 Log medio biótico Red Natura (en vivo)",
                height=220
            )
            # Esperar hasta que el campo se complete
            for _ in range(5):
                time.sleep(1)
                data_actual = load_json(json_path)
                if data_actual.get("4.3_Medio_biotico"):
                    break
            st.success("🪶 Medio biótico/perceptual/socioeconómico (Red Natura) generado.")
        except Exception as e:
            st.error(f"Error generando medio biótico (Red Natura): {e}")

    else:
        st.warning("⚠️ Fuera de Red Natura 2000. Generando medio biótico estándar…")
        try:
            run_script_streaming(
                [sys.executable, "-u", "core/sintesis/medio_biotico_no_red_natura.py", str(json_path)],
                ui_title="🪶 Log medio biótico (fuera Red Natura)",
                height=220
            )
            for _ in range(5):
                time.sleep(1)
                data_actual = load_json(json_path)
                if data_actual.get("4.3_Medio_biotico"):
                    break
            st.success("🪶 Medio biótico/perceptual/socioeconómico (fuera Red Natura) generado.")
        except Exception as e:
            st.error(f"Error generando medio biótico: {e}")

    data_actual = load_json(json_path)
    update_json_field(json_path, {
        "4.3_Medio_biotico": data_actual.get("4.3_Medio_biotico", ""),
        "4.4_Medio_perceptual": data_actual.get("4.4_Medio_perceptual", ""),
        "4.5_Medio_socioeconomico": data_actual.get("4.5_Medio_socioeconomico", "")
    })

    if any(data_actual.values()):
        st.text_area("🌱 4.3 Medio biótico", data_actual.get("4.3_Medio_biotico", ""), height=160)
        st.text_area("👁️ 4.4 Medio perceptual", data_actual.get("4.4_Medio_perceptual", ""), height=130)
        st.text_area("👥 4.5 Medio socioeconómico", data_actual.get("4.5_Medio_socioeconomico", ""), height=140)

# ========================
# 🌾 USOS ACTUALES DEL TERRENO
# ========================
st.markdown("## 🌾 Usos actuales del terreno")

if json_path.exists():
    st.write(f"📄 Archivo en uso: `{json_path.name}`")

    boton_usos = st.button("🧠 Generar 'Usos actuales' automáticamente")

    if boton_usos:
        with st.spinner("Generando texto y captura desde visor CH Duero..."):
            script_usos_path = find_script("core/sintesis/usos_actuales_llm.py")
            cmd = [sys.executable, "-u", script_usos_path, str(json_path)]
            run_script_streaming(
                cmd,
                ui_title="🗺️ Proceso de generación de 'Usos actuales del terreno'",
                height=300
            )

        # 🔄 Recargar JSON actualizado tras la ejecución
        data_prev = load_json(json_path)
        update_json_field(json_path, {
            "usos_actuales_llm": data_prev.get("usos_actuales_llm", ""),
            "captura_usos_actuales": data_prev.get("captura_usos_actuales", "")
        })

        # ✅ Mensaje de confirmación
        st.success("✅ Captura guardada correctamente.")

else:
    st.warning("⚠️ No se encontró el archivo JSON cargado.")

# ========================
# 💧 INFORMACIÓN DE AGUAS
# ========================
st.markdown("## 💧 Información de aguas (Confederación Hidrográfica del Duero)")

if json_path.exists():
    st.write(f"📄 Archivo en uso: `{json_path.name}`")

    boton_conf = st.button("💧 Obtener información hidrogeológica automáticamente")

    if boton_conf:
        with st.spinner("Consultando visor CH Duero y extrayendo información hidrogeológica..."):
            script_conf_path = find_script("core/export_info_confederacion.py")
            cmd = [sys.executable, "-u", script_conf_path, str(json_path)]
            run_script_streaming(
                cmd,
                ui_title="💧 Proceso de extracción de información de Confederación",
                height=300
            )

        # 🔄 Recargar JSON actualizado tras la ejecución
        data_prev = load_json(json_path)
        update_json_field(json_path, {
            "confederacion_info": data_prev.get("confederacion_info", "")
        })

        # ✅ Mensaje de confirmación
        if data_prev.get("confederacion_info"):
            st.success("✅ Información hidrogeológica extraída y guardada correctamente.")
        else:
            st.warning("⚠️ No se encontró información de Confederación (puede que el visor no haya devuelto datos).")

else:
    st.warning("⚠️ No se encontró el archivo JSON cargado.")


# ========================
# EXPORTAR DOCX FINAL
# ========================
st.markdown("---")
st.subheader("🧾 Exportar documento final")

placeholders_final = load_json(json_path)
hoy = datetime.now().strftime("%Y%m%d")
base = f"EIA_simplificada_{hoy}"
docx_path = Path("outputs") / f"{base}.docx"

# Botón estilizado ancho completo
st.markdown(
    """
    <style>
    div.stButton > button:first-child { width: 100%; }
    </style>
    """,
    unsafe_allow_html=True
)

if st.button("💾 Generar DOCX final"):
    with st.spinner("🧠 Preparando y generando el documento..."):
        try:
            res = subprocess.run(
                [sys.executable, "-u", "core/sintesis/redactar_placeholder.py"],
                capture_output=True, text=True, cwd=str(PROJECT_ROOT), timeout=300
            )
            if res.returncode == 0:
                st.success("✅ Redacción técnica completada.")
            else:
                st.warning("⚠️ Hubo avisos en la redacción. Revisa el log si es necesario.")
        except Exception as e:
            st.error(f"❌ Error durante la redacción automática: {e}")

    placeholders_final = load_json(json_path)
    with st.spinner("📄 Generando documento Word final..."):
        export_docx_from_placeholder_map(
            placeholder_map=placeholders_final,
            plantilla_path="plantilla_EIA.docx",
            out_path=str(docx_path)
        )

    st.success("📄 Documento exportado correctamente.")
    with open(docx_path, "rb") as f:
        st.download_button(
            "⬇️ Descargar DOCX generado",
            data=f,
            file_name=f"{base}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
