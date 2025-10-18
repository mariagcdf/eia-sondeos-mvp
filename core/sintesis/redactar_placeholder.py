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
# 🔹 PROMPTS EXISTENTES
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
# 🔹 NUEVO PROMPT: IMPACTO SOBRE LA POBLACIÓN (fase de funcionamiento)
# ==============================================================
PROMPT_POBLACION = """
Eres un redactor técnico ambiental.
Redacta el apartado “Impacto sobre la población” de la fase de funcionamiento
de un Estudio de Impacto Ambiental, basándote en el uso del sondeo indicado.

=== DATOS ===
Uso del sondeo: {uso_sondeo}

=== INSTRUCCIONES ===
1. Redacta un texto formal, técnico y claro, sin usar Markdown ni HTML. No pongas títulos, comienza directamente con el texto.
2. Incluye:
   • Descripción del impacto social.
   • Tipo de efecto (positivo o negativo, directo, duración, reversibilidad).
   • Dictamen y valoración final (admisible y compatible, moderado, etc.).
3. Si el uso es:
   - Abastecimiento → enfoca en el suministro de agua y bienestar poblacional.
   - Riego o agrícola → enfoca en eficiencia hídrica y desarrollo agrario.
   - Industrial → enfoca en empleo y economía local.
   - Recreativo o deportivo → enfoca en turismo y ocio.
   - Otro → redacta un texto genérico positivo.
4. Usa saltos de párrafo dobles (\\n\\n) para formato Word.
"""
PROMPT_CESE_SOCIAL = """
Eres un redactor técnico ambiental especializado en Evaluaciones de Impacto Ambiental.
Redacta el texto correspondiente al impacto social, económico y cultural en la FASE DE CESE
de un proyecto, teniendo en cuenta el uso descrito.

=== USO DEL PROYECTO ===
{uso_sondeo}

=== INSTRUCCIONES ===
1. Redacta un párrafo formal y técnico de 4–6 líneas.
2. Describe las consecuencias del cese de la actividad sobre la población, la economía local o los servicios.
3. Si el cese no implica pérdida de un recurso esencial, indícalo claramente.
4. Finaliza con el dictamen y valoración (admisible y compatible, moderado, etc.).
5. No uses Markdown ni HTML, solo texto plano con saltos de línea válidos para Word.
"""
PROMPT_RESUMEN = """
Eres un redactor técnico ambiental especializado en estudios de impacto ambiental.
Redacta el texto del RESUMEN FINAL del estudio, adaptándolo al uso indicado a continuación.

=== USO DEL PROYECTO ===
{uso_sondeo}

=== INSTRUCCIONES ===
1. Mantén la estructura general siguiente, pero adapta el contenido técnico y social al uso concreto:
   - Indica que no se han identificado impactos críticos.
   - Señala que los efectos son compatibles o moderados.
   - Explica brevemente por qué (baja entidad, duración limitada, medidas preventivas, etc.).
   - Describe los posibles impactos en la fase de cese, adaptados al uso (por ejemplo, si el sondeo es para riego, abastecimiento, recreativo o industrial).
   - Finaliza con una conclusión sobre la razonabilidad del proyecto y su compatibilidad ambiental.
2. El texto debe tener entre 8 y 10 líneas, en tono formal y técnico.
3. No uses Markdown ni HTML, solo texto plano con saltos de línea aptos para Word.
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
        texto_final = (
        texto_final
        .replace("\\t", "\t")    # 🔹 Convierte las secuencias "\t" literales en tabuladores reales
        .replace("•", "·")
        .replace("x", "x")
        .replace("l/", "L/")
        .replace("m3", "m³")
        .strip()
        )

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

    # === NUEVO: impacto_poblacion ===

    # Buscar de forma flexible en todas las claves posibles
    detalles_de_uso = (
        data.get("parametros.detalles_de_uso") or
        data.get("parametros.uso_previsto") or
        (data.get("parametros", {}).get("detalles_de_uso") if isinstance(data.get("parametros"), dict) else "") or
        (data.get("parametros", {}).get("uso_previsto") if isinstance(data.get("parametros"), dict) else "") or
        ""
    ).strip()

    if detalles_de_uso:
        print(f"Generando texto de impacto sobre la población (uso: {detalles_de_uso})...")

        # 🔹 Asegúrate de que el prompt use {uso_sondeo}, no {detalles_de_uso}
        prompt = PROMPT_POBLACION.format(uso_sondeo=detalles_de_uso)

        respuesta = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
        )

        texto_final = respuesta.choices[0].message.content.strip()
        texto_final = re.sub(r"\n{3,}", "\n\n", texto_final).replace("\r", "")

        data["impacto_poblacion"] = texto_final
        print("impacto_poblacion generado correctamente.")
    else:
        print("No se encontró ningún campo de uso en el JSON. Se omite impacto_poblacion.")


    # === NUEVO: impacto_cese_social ===
    uso_sondeo = (
        data.get("parametros.detalles_de_uso") or
        data.get("parametros.uso_previsto") or
        (data.get("parametros", {}).get("detalles_de_uso") if isinstance(data.get("parametros"), dict) else "") or
        (data.get("parametros", {}).get("uso_previsto") if isinstance(data.get("parametros"), dict) else "") or
        ""
    ).strip()

    if uso_sondeo:
        print(f"Generando texto de impacto social en fase de cese (uso: {uso_sondeo})...")

        prompt = PROMPT_CESE_SOCIAL.format(uso_sondeo=uso_sondeo)

        respuesta = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
        )

        texto_final = respuesta.choices[0].message.content.strip()
        texto_final = re.sub(r"\n{3,}", "\n\n", texto_final).replace("\r", "")

        data["impacto_cese_social"] = texto_final
        print("impacto_cese_social generado correctamente.")
    else:
        print("No se encontró ningún campo de uso en el JSON. Se omite impacto_cese_social.")


        # === Guardar JSON actualizado ===
        with open(latest_json, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print("\nJSON actualizado con formato técnico listo para exportar a Word.\n")
        return latest_json

    # === NUEVO: resumen_final ===
    uso_sondeo = (
        data.get("parametros.detalles_de_uso") or
        data.get("parametros.uso_previsto") or
        (data.get("parametros", {}).get("detalles_de_uso") if isinstance(data.get("parametros"), dict) else "") or
        (data.get("parametros", {}).get("uso_previsto") if isinstance(data.get("parametros"), dict) else "") or
        ""
    ).strip()

    if uso_sondeo:
        print(f"Generando resumen final adaptado al uso (uso: {uso_sondeo})...")

        prompt = PROMPT_RESUMEN.format(uso_sondeo=uso_sondeo)

        respuesta = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
        )

        texto_final = respuesta.choices[0].message.content.strip()
        texto_final = re.sub(r"\n{3,}", "\n\n", texto_final).replace("\r", "")

        data["resumen_final"] = texto_final
        print("resumen_final generado correctamente.")
    else:
        print("No se encontró ningún campo de uso en el JSON. Se omite resumen_final.")

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
