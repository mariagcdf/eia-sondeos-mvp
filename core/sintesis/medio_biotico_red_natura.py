import sys
import json
import time
from pathlib import Path
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from typing import Optional, Dict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from core.extraccion.llm_utils import call_llm_extract_json


def fetch_sdf_data_api(es_code: str) -> Optional[Dict]:
    """Intenta obtener la ficha del SDF desde el endpoint público (descarga XML y lo convierte a texto)."""
    url = f"https://natura2000.eea.europa.eu/Natura2000/SDF.aspx?site={es_code}"
    print(f"RN_STEP: Intentando obtener datos del SDF desde el endpoint XML: {url}")
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            print(f"RN_STEP: Ficha SDF obtenida correctamente ({es_code})")
            return {"texto_bruto": resp.text}
        else:
            print(f"RN_WARN: No se pudo acceder al XML del SDF (HTTP {resp.status_code})")
    except Exception as e:
        print(f"RN_ERROR: No se pudo acceder al XML del SDF -> {e}")
    return None


def fetch_sdf_html(es_code: str) -> str:
    """Abre el visor web de Natura 2000 y extrae el texto visible del SDF."""
    url = f"https://natura2000.eea.europa.eu/Natura2000/sdf/#/sdf?site={es_code}&release=55"
    print(f"RN_STEP: Abriendo visor SDF web: {url}")
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(url)
        time.sleep(6)
        body_text = driver.find_element(By.TAG_NAME, "body").text
        driver.quit()
        print("RN_STEP: Texto extraído correctamente desde el visor web.")
        return body_text
    except Exception as e:
        print(f"RN_ERROR: Fallo al usar Selenium -> {e}")
        return "No se pudo extraer información del visor Natura 2000."


def generar_medio_biotico_red_natura(json_path: str):
    """Genera los apartados 4.3, 4.4 y 4.5 del EIA usando el texto del SDF."""
    json_path = Path(json_path)
    data = json.loads(json_path.read_text(encoding="utf-8"))

    es_code = data.get("codigo_red_natura") or data.get("codigos_red_natura", [""])[0]
    if not es_code:
        raise ValueError("No se encontró código Red Natura en el JSON.")

    print(f"RN_STEP: Código identificado: {es_code}")

    sdf_info = fetch_sdf_data_api(es_code)

    # Si la API falla, intenta el visor
    if not sdf_info or not sdf_info.get("texto_bruto"):
        print("RN_STEP: Intentando extraer texto desde el visor web (Selenium)…")
        sdf_text = fetch_sdf_html(es_code)
        sdf_info = {"texto_bruto": sdf_text}

    
    # 🔹 Filtra solo lo relevante (sin menús ni cabeceras)
    lineas = [
        l.strip() for l in sdf_info.get("texto_bruto", "").splitlines()
        if l.strip() and not l.lower().startswith(("european environment", "search", "natura 2000", "english", "login"))
    ]
    texto_filtrado = "\n".join(lineas)

    sdf_info = {"texto_bruto": texto_filtrado}

    prompt = f"""
    Eres un experto en evaluación ambiental y redactas Estudios de Impacto Ambiental (EIA) de acuerdo con la legislación española y la normativa europea.

    A partir de la siguiente información oficial del espacio Natura 2000 (código {es_code}),
    redacta los siguientes apartados del EIA simplificado:

    - **4.3 Medio biótico:** describe con rigor técnico y detalle la vegetación, fauna, hábitats, ecosistemas, endemismos, especies protegidas y su relevancia ecológica. 
    Incluye referencias a la tipología de hábitats (Directiva 92/43/CEE), su estado de conservación y conectividad ecológica. Extensión recomendada: 400-600 palabras.

    - **4.4 Medio perceptual:** analiza en profundidad el paisaje, unidades visuales, relieve, visibilidad desde accesos y poblaciones, calidad escénica y fragilidad visual.
    Incluye apreciaciones estéticas y perceptuales justificadas. Extensión recomendada: 250-400 palabras.

    - **4.5 Medio socioeconómico:** describe el uso actual del suelo, actividades agrícolas, ganaderas, turísticas o extractivas, infraestructuras existentes,
    población, dinámica demográfica, y relación con el entorno rural o urbano. Extensión recomendada: 300-500 palabras.

    Devuelve la respuesta *EXCLUSIVAMENTE* en formato JSON válido con la estructura exacta:

    {{
    "4.3": "texto completo del medio biótico",
    "4.4": "texto completo del medio perceptual",
    "4.5": "texto completo del medio socioeconómico"
    }}

    No incluyas explicaciones, notas ni comentarios fuera del JSON. 
    Evita frases genéricas y desarrolla cada sección como si formara parte del cuerpo de un informe profesional.

    Información base del SDF o XML:
    {sdf_info.get("texto_bruto", "")[:12000]}
    """

    print("RN_STEP: Enviando texto al modelo LLM para redacción…")

    try:
        texto_generado = call_llm_extract_json(prompt)
    except Exception as e:
        print(f"RN_WARN: El modelo no devolvió JSON válido ({e}). Reintentando en modo texto libre…")
        texto_generado = call_llm_extract_json(prompt)

    if isinstance(texto_generado, dict):
        data["4.3_Medio_biotico"] = texto_generado.get("4.3", "")
        data["4.4_Medio_perceptual"] = texto_generado.get("4.4", "")
        data["4.5_Medio_socioeconomico"] = texto_generado.get("4.5", "")
    else:
        # Si viene como texto libre
        secciones = {
            "4.3_Medio_biotico": "",
            "4.4_Medio_perceptual": "",
            "4.5_Medio_socioeconomico": ""
        }
        partes = texto_generado.split("4.4")
        if len(partes) > 1:
            secciones["4.3_Medio_biotico"] = partes[0]
            resto = partes[1].split("4.5")
            if len(resto) > 1:
                secciones["4.4_Medio_perceptual"] = resto[0]
                secciones["4.5_Medio_socioeconomico"] = resto[1]
        else:
            secciones["4.3_Medio_biotico"] = texto_generado

        data.update(secciones)

    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Apartados 4.3-S4.5 generados correctamente.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python medio_biotico_red_natura.py <ruta_json>")
        sys.exit(1)

    generar_medio_biotico_red_natura(sys.argv[1])
