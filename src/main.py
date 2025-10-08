
import argparse, yaml
import geopandas as gpd
from pathlib import Path
from .ingest import load_projects_csv
from .analysis import analyze_project
from .report import render_report

def parse_args():
    ap = argparse.ArgumentParser(description="EIA Sondeos MVP")
    ap.add_argument("--input", required=True, help="CSV de proyectos (lon/lat en EPSG:4326)")
    ap.add_argument("--layers-dir", default="data/layers", help="Carpeta con capas GeoJSON/Shapefile")
    ap.add_argument("--rules", default="config/rules.yaml", help="Reglas YAML")
    ap.add_argument("--templates", default="templates", help="Carpeta de plantillas Jinja2")
    ap.add_argument("--output", default="outputs", help="Carpeta de salida")
    return ap.parse_args()

def main():
    args = parse_args()
    projects = load_projects_csv(args.input)

    # Cargar reglas
    with open(args.rules, "r", encoding="utf-8") as f:
        rules = yaml.safe_load(f) or {}

    # Rutas de capas
    layers = {
        "rivers": str(Path(args.layers_dir) / "rivers.geojson"),
        "natura": str(Path(args.layers_dir) / "natura.geojson"),
    }

    # Procesar cada proyecto
    for idx in range(len(projects)):
        row = projects.iloc[[idx]]
        result = analyze_project(row, layers, rules)

        context = {
            **result,
            "titulo": "Evaluación Preliminar de Afecciones Ambientales (Sondeo)",
            "resumen": "Informe automático de pre-screening para oficina técnica. Datos de entrada y reglas simples.",
            "afecciones": [
                {"componente":"Hidrología","metrica":"Distancia a cauce (m)", "valor": result["distancia_cauce_m"], "riesgo": result["riesgo_hidrologico"]},
                {"componente":"Biótico","metrica":"Intersección Red Natura", "valor": "Sí" if result["en_red_natura"] else "No", "riesgo": result["riesgo_biotico"]},
            ]
        }
        outpath = render_report(args.output, args.templates, context)
        print(f"[OK] Informe generado: {outpath}")

if __name__ == "__main__":
    main()
