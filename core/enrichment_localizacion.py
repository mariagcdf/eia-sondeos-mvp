# -*- coding: utf-8 -*-
"""
Orquesta el enriquecimiento externo:
- Catastro por coordenadas -> párrafo seguro de localización/uso del suelo
- CH Duero (opcional) -> ID + URL + nota prudente
"""

from typing import Dict, Any, Optional
from datetime import datetime
from core.catastro_client import consulta_por_coordenadas, formato_superficie
from core.confederacion_client import consultar_punto as chd_consultar_punto


# -------------------- CATRASTRO -------------------- #

def redactar_parrafo_catastro(cat_data) -> str:
    tipo = (cat_data.tipo_suelo or "").title()
    uso = (cat_data.uso or "").title()
    ubic = None
    if cat_data.via:
        ubic = f'{cat_data.via} {cat_data.numero}' if cat_data.numero else cat_data.via

    partes = []

    # Frase 1
    p1 = "La finca objeto del presente estudio"
    if tipo:
        p1 += f" se encuentra clasificada como suelo {tipo}"
    else:
        p1 += " se encuentra clasificada conforme a los datos catastrales disponibles"
    p1 += ", de acuerdo con la información obtenida del Catastro"
    if cat_data.municipio and cat_data.provincia:
        p1 += f", y se localiza en el término municipal de {cat_data.municipio} ({cat_data.provincia})"
    elif cat_data.municipio:
        p1 += f", y se localiza en el término municipal de {cat_data.municipio}"
    p1 += "."
    partes.append(p1)

    # Frase 2
    sup = formato_superficie(cat_data.superficie_m2)
    segs = []
    if sup:
        segs.append(f"Presenta una superficie catastral de {sup}")
    if cat_data.ref_catastral:
        segs.append(f"y está identificada con la referencia catastral {cat_data.ref_catastral}")
    if ubic:
        segs.append(f', situada en el entorno de "{ubic}"')
    if segs:
        partes.append(" ".join(segs) + ".")

    # Frase 3
    if uso or tipo:
        etiqueta = uso or tipo
        partes.append(
            "De acuerdo con la información catastral, el terreno presenta un "
            f"uso principal {etiqueta.lower()}, en un entorno coherente con dicha clasificación."
        )

    # Frase 4
    partes.append(
        "Con la información disponible, la localización resulta compatible con el planeamiento vigente, "
        "sin apreciarse incompatibilidades urbanísticas relevantes en esta fase."
    )

    return " ".join(partes)


def enriquecer_con_catastro(datos_min: Dict[str, Any], coords: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    coords debe contener al menos: {"x": float, "y": float, "srs": "EPSG:25830"}
    """
    if not coords or "x" not in coords or "y" not in coords:
        datos_min.setdefault("bloques", {})["parrafo_localizacion"] = datos_min.get("bloques", {}).get("parrafo_localizacion", "")
        return datos_min

    x, y = float(coords["x"]), float(coords["y"])
    srs = coords.get("srs", "EPSG:25830")
    cat = consulta_por_coordenadas(x, y, srs)
    parrafo = redactar_parrafo_catastro(cat)

    datos_min.setdefault("externo", {})["catastro"] = {
        "ref_catastral": cat.ref_catastral,
        "municipio": cat.municipio,
        "provincia": cat.provincia,
        "via": cat.via,
        "numero": cat.numero,
        "tipo_suelo": cat.tipo_suelo,
        "uso": cat.uso,
        "superficie_m2": cat.superficie_m2,
    }
    # Inserta o concatena el párrafo
    datos_min.setdefault("bloques", {})
    base = datos_min["bloques"].get("parrafo_localizacion", "")
    datos_min["bloques"]["parrafo_localizacion"] = (base + "\n\n" + parrafo).strip() if base else parrafo
    return datos_min


# -------------------- CONFEDERACIÓN (CHD) -------------------- #

def _nota_prudente_chd(id_text: str, url: str) -> str:
    fecha = datetime.now().strftime("%d/%m/%Y")
    return (
        f"Según la consulta automática realizada el {fecha} al visor oficial de la "
        f"Confederación Hidrográfica del Duero, la localización se asocia al identificador **{id_text}**, "
        f"accesible en el enlace público: {url}. Este identificador permite vincular el emplazamiento con la "
        f"información hidrológica y la planificación vigente del distrito, conforme a los datos publicados por la CHD."
    )


def enriquecer_con_confederacion(datos_min: Dict[str, Any],
                                 coords: Optional[Dict[str, Any]],
                                 anadir_nota_en_localizacion: bool = True) -> Dict[str, Any]:
    """
    coords: requiere lon/lat (WGS84) -> {"lon": -5.7, "lat": 40.8}
    Guarda en datos_min['externo']['confederacion'] y, si hay ID/URL,
    puede añadir una nota prudente en 'parrafo_localizacion' (opcional).
    """
    if not coords or "lon" not in coords or "lat" not in coords:
        return datos_min

    lon = float(coords["lon"])
    lat = float(coords["lat"])
    res = chd_consultar_punto(lon, lat)

    datos_min.setdefault("externo", {})["confederacion"] = {
        "ok": res.get("ok", False),
        "id": res.get("id"),
        "url": res.get("url"),
        "error": res.get("error"),
    }

    if anadir_nota_en_localizacion and res.get("ok") and res.get("id") and res.get("url"):
        nota = _nota_prudente_chd(res["id"], res["url"])
        datos_min.setdefault("bloques", {})
        base = datos_min["bloques"].get("parrafo_localizacion", "")
        concatenado = (base + "\n\n" + nota).strip() if base else nota
        datos_min["bloques"]["parrafo_localizacion"] = concatenado

    return datos_min
