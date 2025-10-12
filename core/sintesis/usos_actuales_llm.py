# core/sintesis/redactar_usos_actuales.py
import sys
from pathlib import Path
import json
import re
import time

sys.path.append(str(Path(__file__).resolve().parents[2]))

from core.extraccion.llm_utils import get_client
from core.sintesis.captura_chduero import captura_chduero

client = get_client()

# ==============================================================
# 🔹 FUNCIÓN PRINCIPAL
# ==============================================================
def redactar_usos_actuales():
    output_dir = Path("outputs")
    json_files = sorted(output_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not json_files:
        raise FileNotFoundError("❌ No se encontró ningún archivo JSON en outputs.")

    latest_json = json_files[0]
    print(f"📂 Usando JSON más reciente: {latest_json.name}")

    with open(latest_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    # --- Datos de contexto ---
    municipio = data.get("municipio", "")
    provincia = data.get("provincia", "")
    refcat = data.get("referencia_catastral", "")
    superficie = data.get("superficie", "")
    captura = data.get("captura_chduero", "")

    contexto = []
    if municipio:
        contexto.append(f"Municipio: {municipio}")
    if provincia:
        contexto.append(f"Provincia: {provincia}")
    if refcat:
        contexto.append(f"Referencia catastral: {refcat}")
    if superficie:
        contexto.append(f"Superficie catastral: {superficie}")
    if captura:
        contexto.append(f"Existe una captura aérea (imagen adjunta) del entorno.")

    contexto_txt = "\n".join(contexto) if contexto else "Sin datos adicionales."

    # --- Prompt dinámico ---
    prompt = f"""
Eres un redactor técnico especializado en estudios de impacto ambiental.
Redacta el bloque “Usos actuales del terreno” de un informe ambiental,
basándote en los siguientes datos reales de localización y características de la parcela:

=== CONTEXTO ===
{contexto_txt}

=== INSTRUCCIONES ===
1. Describe de forma objetiva:
   - Clasificación urbanística y localización general (urbano, rústico, industrial, etc.).
   - Uso actual del suelo (agrícola, forestal, improductivo, etc.).
   - Cobertura vegetal y grado de alteración.
   - Existencia de edificaciones o instalaciones.
   - Relación con el entorno inmediato (otras parcelas, caminos, núcleos urbanos).
2. Usa un tono técnico, impersonal y claro.
3. Estructura el texto en 2 a 4 párrafos, con doble salto de línea entre ellos.
4. No inventes datos administrativos o técnicos fuera del contexto dado.
5. Finaliza con una breve valoración sobre la idoneidad del emplazamiento para la actuación.
"""

    print("📝 Redactando bloque 'Usos actuales del terreno' con contexto real...")
    respuesta = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}],
    )

    texto_final = respuesta.choices[0].message.content.strip()
    texto_final = re.sub(r"\n{3,}", "\n\n", texto_final)
    texto_final = texto_final.replace("\r", "")

    # --- Guardar texto en el JSON ---
    data["PH_usos_actuales"] = texto_final
    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("✅ Bloque 'Usos actuales del terreno' redactado correctamente.")

    # --- Captura CH Duero (si no existe aún) ---
    if not captura:
        print("🌍 Generando captura CH Duero...")
        try:
            captura_path = captura_chduero()
            data["captura_chduero"] = captura_path.name
            with open(latest_json, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"🖼️ Captura añadida: {captura_path}")
        except Exception as e:
            print(f"⚠️ No se pudo generar la captura CH Duero: {e}")
    else:
        print("🖼️ Captura ya existente, no se repite la descarga.")

    print(f"Archivo actualizado: {latest_json.name}")
    return latest_json


# ==============================================================
# 🔹 EJECUCIÓN DIRECTA
# ==============================================================
if __name__ == "__main__":
    redactar_usos_actuales()
