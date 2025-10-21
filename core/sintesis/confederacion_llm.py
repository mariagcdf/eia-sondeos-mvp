import sys
import json
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from core.extraccion.llm_utils import llm_chat  # ✅ cambio clave


def generar_masas_agua_afectadas(json_path: str):
    """Genera automáticamente el epígrafe 'Masas de agua afectadas' usando la información de Confederación."""
    json_path = Path(json_path)
    if not json_path.exists():
        raise FileNotFoundError(f"No se encontró el archivo JSON: {json_path}")

    data = json.loads(json_path.read_text(encoding="utf-8"))
    conf_info = data.get("confederacion_info", {})

    if not conf_info:
        raise ValueError("No se encontró información de Confederación en el JSON (confederacion_info está vacío).")

    print("RN_STEP: Datos de Confederación cargados correctamente.")
    time.sleep(1)

    TEXTO_BASE = """
La zona donde se sitúa el sondeo proyectado no pertenece a ninguna Unidad Hidrogeológica. La subzona 31900009 corresponde con la n° 6, denominada "Pisuerga”.
La masa de agua subterránea donde se emplaza el sondeo es la número 400006, denominada "Valdavia". Dicha masa de agua ocupa el sector centro-oriental de la provincia de Palencia, entre los ríos Carrión y Pisuerga. El límite norte lo forman las sierras de la Cordillera Cantábrica y el sur las estribaciones del Páramo de Astudillo.
Se estiman unos recursos disponibles en esta masa de agua de 174,48 hm3/año, mientras que el volumen de concesiones y autorizaciones otorgadas por la Confederación Hidrográfica del Duero en esta masa suponen un régimen de explotación de 7,973 hm3/año, pero, sin embargo, su índice de explotación en cuanto a volumen demandado es de 0,04.
La evaluación del Estado cuantitativo y cualitativo a fecha más reciente (2013) se considera esta masa como en buen estado general por no encontrarse alteraciones relevantes que afecten a la totalidad de la misma. A continuación, se especifica más detalladamente.

Estado cuantitativo de la masa “Valdavia”

Designación definitiva del estado cuantitivo de la masa subterránea: Bueno

-Justificación a la asignación definitiva:

Índice de explotación inferior a 0,8 (0,16). Tendencia a largo plazo relativamente decreciente, pero con cambio de tendencia en los últimos 20 años. Las tendencias piezométricas del modelo no son significativas. La previsión no es clara. En sucesivas actualizaciones de la red de piezometría, y con el aumento del 


Estado cualitativo de la masa “Valdavia”

Designación definitiva del estado químico de la masa subterránea: Bueno

-Justificación a la asignación definitiva:

No detectan valores que excedan las normas de calidad y/o los valores umbral propuestos para esta masa. No se encuentran evidencias de salinización. No se considera afección sobre las MSPF asociadas a aguas subterráneas, etc.
 

Hidrogeología

Limita al norte con el dominio cantábrico representado por los materiales paleozoicos de las masas de Cervera de Pisuerga y mesozoicos de la masa de Quintanilla-Peñahoradada. Al sur con las estribaciones del Páramo de Astudillo, al este y oeste con las masas de Villadiego y Carrión respectivamente.

Los materiales cuaternarios (terrazas y aluviales) presentan una permeabilidad media, no obstante, su escasa potencia, así como su disposición espacial, reducen el interés hidrológico de estos materiales que funcionan como acuíferos colgados (terrazas) o bien relacionados con los cauces de los ríos (aluviales y terrazas más bajas), que son explotados tradicionalmente mediante pozos excavados de gran diámetro, para el riego de pequeñas huertas. El sistema está constituido por sedimentos detríticos terciarios a modo de lentejones de arenas dispersos en una matriz arcillo-limosa, donde los primeros constituyen niveles acuíferos mientras que la matriz se comporta como un acuitardo. La distribución, potencia y frecuencia de los lentejones arenosos condiciona tanto los parámetros hidráulicos como el funcionamiento del acuífero. El conjunto se comporta como un acuífero multicapa, heterogéneo y anisótropo, confinado o semiconfinado según zonas. Los datos litológicos aportados por los sondeos reflejan que los mejores niveles acuíferos se localizan por debajo de los 100 m de profundidad.

Repercusiones a largo plazo sobre el estado de las masas de agua afectadas

Teniendo en cuenta las anteriores consideraciones, extraídas de la aplicación MIRAME de Confederación Hidrográfica del Duero y del IGME en la Hoja n°197 del Mapa Topográfico Nacional de España, “Carrión de los Condes”, se encuentra la masa de agua subterránea “Valdavia”

Se considera una masa con índice de explotación (volumen demandado) bajo, situándose el mismo en 0,04. Por lo que el recurso disponible se considera mayor que el derecho de explotación.

A largo plazo se puede considerar una disminución del nivel piezométrico debido a la sobre explotación de dichas masas subterráneas, pero muy a largo plazo por los escasos sondeos disponibles en la zona.

El organismo encargado de gestionar el recurso disponible y las concesiones de extracción de aguas subterráneas es la Confederación Hidrográfica del Duero, para lo cual se exige la implantación de un dispositivo de control del volumen de agua extraído. En el caso de que la zona de “Valdavia” comenzase a estar sobreexplotada, se consideraría por parte de la Confederación Hidrográfica del Duero, cerrar el acuífero y no permitir más extracciones de agua. 

La zona de Loma de Ucieza está considerada como zona libre de limitaciones en la cual se pueden considerar las obras de captación de aguas subterráneas. Además, en las medidas normativas de Protección del estado cuantitativo de las masas de agua subterránea y Protección frente a la contaminación difusa de las masas de agua, de periodo de ejecución 2022-2027 se ha considerado sin necesidades de inversión.
"""

    prompt = f"""
Eres un ingeniero ambiental especializado en hidrogeología y redactas Estudios de Impacto Ambiental.

A partir de los siguientes datos oficiales extraídos de la Confederación Hidrográfica del Duero:

{json.dumps(conf_info, indent=2, ensure_ascii=False)}

Redacta el epígrafe **"Masas de agua afectadas"** siguiendo *exactamente* el estilo, estructura y tono técnico del texto base:

{TEXTO_BASE}

Requisitos:
- Mantén los mismos apartados y extensión aproximada.
- Sustituye nombres, códigos, límites, cifras y características hidrogeológicas por los valores reales del JSON.
- Si algún dato falta, usa una redacción neutra o genérica, sin inventar lugares ficticios.
- Devuelve solo el texto final en formato plano, sin JSON ni explicaciones adicionales.
- Si un estado de la masa es "malo", obvia esa parte de la redacción.
- Si no hay datos de "hidrogeología", omite ese apartado y ve directamente a Repercusiones a largo plazo...
- No pongas títulos ni encabezados en el texto final.
"""

    print("RN_STEP: Solicitando redacción al modelo…")

    try:
        texto_redactado = llm_chat(prompt)  # ✅ genera texto libre
    except Exception as e:
        print(f"RN_WARN: Error al generar redacción automática ({e})")
        texto_redactado = "No se pudo generar el texto automáticamente."

    data["masas_agua_afectadas"] = texto_redactado.strip()
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    print("RN_DONE: Epígrafe 'Masas de agua afectadas' generado correctamente y guardado en el JSON.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python confederacion_llm.py <ruta_json>")
        sys.exit(1)

    generar_masas_agua_afectadas(sys.argv[1])
