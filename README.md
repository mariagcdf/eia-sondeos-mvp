
# EIA Sondeos MVP (v0.1)

Aplicación mínima para evaluar afecciones ambientales de **sondeos puntuales** a partir de:
- **Coordenadas (lon, lat)** en WGS84 (EPSG:4326)
- Datos básicos de parcela y uso previsto

Cruza el punto con capas **locales** (ejemplo incluido) y genera un **informe HTML** con:
- Distancia a cauces
- Intersección con Red Natura (demo)
- Tabla de riesgos (Alto/Medio/Bajo)

## Requisitos
- Python 3.10+
- (Opcional) geo stack preinstalado vía Conda

## Instalación rápida
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

## Ejecutar demo
```bash
python src/main.py --input data/inputs/sample_projects.csv
```
Salida en `outputs/`.

## Estructura
```
eia-sondeos-mvp/
├── config/
│   └── rules.yaml
├── data/
│   ├── inputs/
│   │   └── sample_projects.csv
│   └── layers/
│       ├── rivers.geojson
│       └── natura.geojson
├── outputs/          # informes aquí
├── src/
│   ├── analysis.py
│   ├── ingest.py
│   ├── report.py
│   ├── utils.py
│   └── main.py
├── templates/
│   └── report.html
└── requirements.txt
```

## Notas
- Las capas de ejemplo son *ficticias* (GeoJSON) y solo sirven para validar el flujo.
- Sustituye `data/layers` por tus capas reales.
