# -*- coding: utf-8 -*-
"""
Cliente Catastro por coordenadas (Consulta_CPMRC).
Devuelve datos básicos (ref catastral, municipio, tipo de suelo, uso, superficie…).
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple
import requests
import xml.etree.ElementTree as ET

CAT_URL = (
    "https://ovc.catastro.meh.es/ovcservweb/OVCSWLocalizacionRC/"
    "OVCCoordenadas.asmx/Consulta_CPMRC"
)
DEFAULT_SRS = "EPSG:25830"  # UTM ETRS89 península
TIMEOUT = 12
HEADERS = {"User-Agent": "EIA-Extractor/1.0 (+uso académico)"}


@dataclass
class CatastroData:
    ref_catastral: Optional[str] = None
    municipio: Optional[str] = None
    provincia: Optional[str] = None
    via: Optional[str] = None
    numero: Optional[str] = None
    tipo_suelo: Optional[str] = None   # Urbano / Rústico…
    uso: Optional[str] = None          # Industrial / Residencial / Agrícola…
    superficie_m2: Optional[float] = None
    raw: Optional[Dict[str, Any]] = None


def _clean(s: Optional[str]) -> Optional[str]:
    return s.strip() if isinstance(s, str) and s.strip() else None


def _first_text(elem, paths, ns):
    for p in paths:
        n = elem.find(p, ns) if ns else elem.find(p)
        if n is not None and n.text and n.text.strip():
            return n.text.strip()
    return None


def _m2_to_areas(superficie_m2: Optional[float]) -> Tuple[Optional[int], Optional[int]]:
    if superficie_m2 is None:
        return None, None
    a = int(superficie_m2 // 100)
    c = int(round(superficie_m2 - a * 100))
    return a, c


def formato_superficie(superficie_m2: Optional[float]) -> Optional[str]:
    if not superficie_m2:
        return None
    a, c = _m2_to_areas(superficie_m2)
    if a is None:
        return f"{int(round(superficie_m2))} m²"
    return f"{int(round(superficie_m2))} m² ({a:02d} áreas y {c:02d} centiáreas)"


def consulta_por_coordenadas(x: float, y: float, srs: str = DEFAULT_SRS) -> CatastroData:
    params = {"SRS": srs, "Coordenada_X": str(x), "Coordenada_Y": str(y)}
    try:
        r = requests.get(CAT_URL, params=params, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
    except requests.RequestException as e:
        return CatastroData(raw={"error": f"HTTP {e}", "params": params})

    try:
        root = ET.fromstring(r.text)
    except ET.ParseError as e:
        return CatastroData(raw={"error": f"XML {e}", "text": r.text[:1000]})

    ns = {"ns": root.tag.split('}')[0].strip('{')} if '}' in root.tag else {}

    candidatos = []
    for path in [".//pc", ".//ns:pc", ".//coordenadas//pc", ".//ns:coordenadas//ns:pc"]:
        candidatos += (root.findall(path, ns) if ns else root.findall(path))

    if not candidatos:
        lerr = _first_text(root, [".//lerr", ".//ns:lerr"], ns)
        return CatastroData(raw={"warning": "Sin candidatos", "lerr": lerr, "xml": r.text[:1000]})

    pc = candidatos[0]
    pc1 = _first_text(pc, ["rc/pc1", "ns:rc/ns:pc1"], ns)
    pc2 = _first_text(pc, ["rc/pc2", "ns:rc/ns:pc2"], ns)
    ref = f"{pc1}{pc2}" if pc1 and pc2 else (pc1 or pc2)

    municipio = _first_text(pc, ["ldtmun", "nm", "muni", "municipio", "nae"], ns)
    provincia = _first_text(pc, ["ldtpro", "prov", "provincia"], ns)
    via = _first_text(pc, ["nv", "via", "tv", "nvia"], ns)
    numero = _first_text(pc, ["pnp", "numero", "hn"], ns)
    tipo = _first_text(pc, ["ldt", "clase", "ts", "tipo_suelo"], ns)
    uso = _first_text(pc, ["luso", "uso", "destino"], ns)
    s_txt = _first_text(pc, ["sfc", "superficie", "sfcpar", "sups"], ns)
    s_m2 = None
    if s_txt:
        try:
            s_m2 = float(str(s_txt).replace(",", "."))
        except Exception:
            s_m2 = None

    return CatastroData(
        ref_catastral=_clean(ref),
        municipio=_clean(municipio),
        provincia=_clean(provincia),
        via=_clean(via),
        numero=_clean(numero),
        tipo_suelo=_clean(tipo),
        uso=_clean(uso),
        superficie_m2=s_m2,
        raw={"xml": r.text[:1200]},
    )
