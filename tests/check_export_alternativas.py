# check_export_alternativas.py
import os
import sys
import json
from datetime import datetime

from core.extraccion.bloques_textuales import extraer_bloques_literal
from core.export_docx_template import export_eia_docx_template
from core.sintesis.alternativas_llm import generar_alternativas_llm

def _load_text(path_txt: str) -> str:
    if not os.path.exists(path_txt):
        raise FileNotFoundError(path_txt)
    with open(path_txt, "r", encoding="utf-8") as f:
        return f.read()

def _load_datos_min(path_json: str | None):
    if not path_json:
        return {
            "localizacion": {"municipio": "Carrascal del Obispo", "provincia": "Salamanca"},
            "parametros": {
                "uso_previsto": "abastecimiento municipal",
                "detalles_de_uso": "Refuerzo de suministro en estiaje",
                "profundidad_proyectada_m": 140,
                "diametro_perforacion_inicial_mm": 215,
                "diametro_perforacion_definitivo_mm": 160,
                "caudal_max_instantaneo_l_s": 0.75,
                "potencia_bombeo_kw": 5.5
            }
        }
    with open(path_json, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    if len(sys.argv) < 3:
        print("Uso: python check_export_alternativas.py <plantilla.docx> <texto.noindex.txt> [datos_min.json]")
        sys.exit(1)

    plantilla = sys.argv[1]
    texto_path = sys.argv[2]
    datos_json = sys.argv[3] if len(sys.argv) >= 4 else None

    if not os.path.exists(plantilla):
        print(f"❌ No existe la plantilla: {plantilla}")
        sys.exit(1)

    if not os.getenv("OPENAI_API_KEY"):
        print("❌ Falta OPENAI_API_KEY en el entorno. Ponla y reintenta.")
        sys.exit(1)

    # 1) Cargar datos mínimos
    datos_min = _load_datos_min(datos_json)

    # 2) Cargar texto (ya extraído) y hacer bloques (aunque aquí nos interesa Alternativas)
    texto = _load_text(texto_path)
    literal_blocks = extraer_bloques_literal(texto)

    # 3) Log rápido de qué tenemos (solo por asegurar)
    print("=== BLOQUES TEXTUALES DISPONIBLES ===")
    for k, v in literal_blocks.items():
        print(f"- {k:16s}: {len(v)} chars")
    print()

    # 4) Generar Alternativas con tu wrapper
    alt_txt = generar_alternativas_llm(datos_min)
    print(f"PH_Alternativas -> {len(alt_txt)} chars")

    # 5) Meterlo en el DOCX junto con el resto
    #    (export_eia_docx_template ya internaliza PH_Alternativas, pero forzamos aquí por si tu versión no lo hace aún)
    literal_blocks["PH_Alternativas"] = alt_txt

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_docx = f"salida_alternativas_{stamp}.docx"
    export_eia_docx_template(datos_min, literal_blocks, plantilla, out_docx)

    print(f"\n✅ DOCX generado: {out_docx}")
    print("   Asegúrate de que en la plantilla existe el placeholder {{PH_Alternativas}}.")

if __name__ == "__main__":
    main()
