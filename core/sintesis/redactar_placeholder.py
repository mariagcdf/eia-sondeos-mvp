import os
import re
import json
import sys
from pathlib import Path
from openai import OpenAI

sys.path.append(str(Path(__file__).resolve().parents[2]))  # asegúrate de que pueda importar 'core'

from core.extraccion.llm_utils import get_client

client = get_client()


# ==============================================================
# 🔹 CARGA SEGURA DE VARIABLES DE ENTORNO
# ==============================================================

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise EnvironmentError(
        "No se encontró la variable OPENAI_API_KEY. "
        "Asegúrate de tener un archivo .env en la raíz con la clave."
    )
else:
    print("Clave OpenAI cargada correctamente.")

# ==============================================================
# 🔹 CONFIGURACIÓN DEL CLIENTE OPENAI
# ==============================================================
client = OpenAI(api_key=api_key)

# ==============================================================
# 🔹 PROMPT PARA PH_CONSUMO
# ==============================================================
PROMPT_CONSUMO = """
Eres un redactor técnico especializado en ingeniería ambiental e hidráulica.
Debes reestructurar y redactar profesionalmente el texto del apartado “Consumo de agua”
de un Estudio de Impacto Ambiental.

=== TEXTO BASE ===
{texto_base}

=== CONTEXTO ===
{contexto}

=== INSTRUCCIONES ===
1. NO inventes ni modifiques cifras, unidades ni conceptos.
2. Reestructura el texto para que siga un formato técnico y legible en Word:
   • Cada bloque importante (CONCEPTOS, CONSUMOS, VOLUMEN NECESARIO, etc.) debe ir en mayúsculas con salto antes y después.
   • Usa tabuladores reales (\\t) para alinear valores a la derecha.
   • Separa los bloques con dos saltos de párrafo (\\n\\n).
3. No uses Markdown, HTML ni símbolos como “**” o “<b>”.
4. Usa saltos de línea reales que funcionen en Word.
"""

# ==============================================================
# 🔹 PROMPT PARA PH_LOCALIZACION
# ==============================================================
PROMPT_LOCALIZACION = """
Eres un redactor técnico ambiental.
Reescribe el texto del apartado “Localización” de un Estudio de Impacto Ambiental
para que tenga formato limpio y legible en Word.

=== TEXTO BASE ===
{texto_base}

=== INSTRUCCIONES ===
1. No cambies nombres, ubicaciones ni coordenadas.
2. Inserta dos saltos de párrafo (\\n\\n) después de cada punto o cambio de idea.
3. No uses Markdown ni HTML, solo texto plano con buena puntuación.
4. Asegúrate de que los saltos sean interpretables en Word.
"""

# ==============================================================
# 🔹 PROCESAMIENTO DE PLACEHOLDERS
# ==============================================================
def procesar_json():
    output_dir = Path("outputs")
    json_files = sorted(output_dir.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not json_files:
        raise FileNotFoundError("No se encontró ningún archivo JSON en outputs/.")

    latest_json = json_files[0]
    print(f"\nUsando JSON más reciente: {latest_json.name}")

    with open(latest_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    contexto = data.get("contexto_general", "Estudio de Impacto Ambiental del proyecto.")

    # === PH_Consumo ===
    if texto_base := data.get("PH_Consumo", "").strip():
        print("Reformateando y redactando PH_Consumo...")
        prompt = PROMPT_CONSUMO.format(texto_base=texto_base, contexto=contexto)
        respuesta = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        texto_final = respuesta.choices[0].message.content.strip()
        texto_final = re.sub(r"\n{3,}", "\n\n", texto_final).replace("\r", "")
        data["PH_Consumo"] = texto_final
        print("PH_Consumo formateado correctamente.")

    # === PH_Localizacion ===
    if texto_base := data.get("PH_Localizacion", "").strip():
        print("Reformateando PH_Localizacion...")
        prompt = PROMPT_LOCALIZACION.format(texto_base=texto_base)
        respuesta = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        texto_final = respuesta.choices[0].message.content.strip()
        texto_final = re.sub(r"\.\s+(?=[A-ZÁÉÍÓÚÑ])", ".\n\n", texto_final)
        texto_final = re.sub(r"\n{3,}", "\n\n", texto_final)
        data["PH_Localizacion"] = texto_final
        print("PH_Localizacion reformateado correctamente.")

    # === Guardar JSON actualizado ===
    with open(latest_json, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("\nJSON actualizado con formato técnico listo para exportar a Word.\n")
    return latest_json


# ==============================================================
# 🔹 EJECUCIÓN DIRECTA
# ==============================================================
if __name__ == "__main__":
    procesar_json()
