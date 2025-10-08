
from math import floor
from pyproj import CRS

def utm_epsg_from_lonlat(lon: float, lat: float) -> int:
    """
    Devuelve el EPSG UTM adecuado (WGS84) para una lon/lat dadas.
    326xx para hemisferio norte, 327xx para sur.
    """
    zone = int(floor((lon + 180) / 6) + 1)
    base = 326 if lat >= 0 else 327
    return int(f"{base}{zone:02d}")

def get_metric_crs_for_point(lon: float, lat: float) -> CRS:
    epsg = utm_epsg_from_lonlat(lon, lat)
    return CRS.from_epsg(epsg)
