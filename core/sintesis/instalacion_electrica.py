# core/sintesis/instalacion_llm.py
from core.extraccion.llm_utils import llm_chat
import json

def redactar_instalacion_llm(datos_min: dict, tipo: str = "fotovoltaica") -> str:
    """
    Redacta un párrafo técnico breve para la sección {{instalacion_electrica}}.
    tipo: 'red' o 'fotovoltaica'.
    """
    loc = (datos_min.get("localizacion") or {})
    muni = loc.get("municipio", "")
    prov = loc.get("provincia", "")

    p = (datos_min.get("parametros") or {})
    potencia_kw = p.get("potencia_bombeo_kw")
    uso = p.get("uso_previsto") or ""
    detalles = p.get("detalles_de_uso") or ""

    contexto = {
        "municipio": muni,
        "provincia": prov,
        "potencia_kw": potencia_kw,
        "uso_previsto": uso,
        "detalles_de_uso": detalles
    }

    modo = "conexión a la red eléctrica de baja tensión existente" if tipo == "red" else "sistema autónomo de generación fotovoltaica con inversor y acumulación"

    prompt = f"""
Redacta un único párrafo (3–6 líneas) con tono técnico formal para una EIA. 
Debe describir la solución de alimentación eléctrica del sondeo, justificando brevemente su idoneidad 
y citando, si procede, la potencia estimada de la bomba. Evita florituras y cifras inventadas.
Cuando sea conexion a red municipal algo asi: El sistema de bombeo del sondeo se alimentará mediante conexión a la red eléctrica municipal, aprovechando la proximidad de la parcela al núcleo urbano. Esta opción garantiza un suministro energético continuo y fiable, con un impacto ambiental mínimo y sin necesidad de instalaciones auxiliares ni acumuladores, asegurando así la operatividad permanente del sistema de captación.
Si es fotovoltaica algo asi: El sistema de bombeo del sondeo se alimentará mediante una instalación fotovoltaica autónoma, diseñada para cubrir las necesidades energéticas de la bomba de agua. Esta solución es especialmente adecuada dada la ubicación del sondeo en una zona con buena radiación solar y la ausencia de conexión a la red eléctrica municipal. La instalación incluirá paneles solares, un inversor y un sistema de acumulación para garantizar el suministro energético durante las horas sin sol, asegurando así la operatividad continua del sistema de captación.

Condiciones del proyecto (si no hay dato, ignóralo con naturalidad):
{json.dumps(contexto, ensure_ascii=False, indent=2)}

Modalidad elegida: "{modo}".

Requisitos de estilo:
- Español de España, terminología de ingeniería.
- Sin títulos ni viñetas.
- Evita detalles constructivos como secciones de cable o número de paneles.
"""
    return llm_chat(prompt)
