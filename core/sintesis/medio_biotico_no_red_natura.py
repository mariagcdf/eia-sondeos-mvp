import json
import sys
from pathlib import Path

# === 1. Verificar argumento de entrada ===
if len(sys.argv) < 2:
    print("❌ Uso: python medio_biotico_no_red_natura.py <ruta_json>")
    sys.exit(1)

json_path = Path(sys.argv[1])
if not json_path.exists():
    print(f"❌ El archivo {json_path} no existe.")
    sys.exit(1)

print(f"📂 Procesando medio biótico para JSON: {json_path.name}")

# === 2. Cargar JSON existente ===
with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

municipio = data.get("municipio", "municipio no especificado")

# === 3. Plantillas base de los apartados ambientales ===
medio_biotico = f"""
En el entorno del término municipal de {municipio}, no se identifican espacios
pertenecientes a la Red Natura 2000 ni otras figuras de protección ambiental relevantes.
La vegetación natural está compuesta por formaciones propias del clima mediterráneo
continental, con predominio de matorrales, pastizales y cultivos de secano. No se prevén
impactos significativos sobre la flora ni sobre hábitats de interés comunitario.
"""

medio_perceptual = f"""
El paisaje del entorno de {municipio} presenta una morfología suave, caracterizada por
una matriz agraria homogénea con cultivos de secano, zonas de pradera y pequeñas
manchas de arbolado disperso. No se observan elementos visuales de especial fragilidad
ni puntos de vista sensibles en el entorno inmediato de actuación.
"""

medio_socioeconomico = f"""
El término municipal de {municipio} presenta un uso mayoritariamente agrícola, con baja
densidad de población y una economía local centrada en la actividad agroganadera.
Las actuaciones previstas no suponen afecciones a infraestructuras básicas ni alteraciones
en el uso del suelo, por lo que se considera nulo el impacto socioeconómico directo.
"""

# === 4. Insertar estructura en el JSON ===
data["medio_ambiental"] = {
    "4.3_Medio_biotico": medio_biotico.strip(),
    "4.4_Medio_perceptual": medio_perceptual.strip(),
    "4.5_Medio_socioeconomico": medio_socioeconomico.strip()
}

# === 5. Guardar cambios ===
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("💾 Información ambiental añadida correctamente al JSON.")
print("✅ Proceso completado (sin Red Natura).")
