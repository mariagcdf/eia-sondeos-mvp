
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point
from shapely.ops import nearest_points
from .utils import get_metric_crs_for_point

def _to_metric(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    # Calcula CRS métrico UTM en función del primer punto (válido para zonas locales)
    lon = float(gdf.geometry.iloc[0].x)
    lat = float(gdf.geometry.iloc[0].y)
    crs_metric = get_metric_crs_for_point(lon, lat)
    return gdf.to_crs(crs_metric)

def load_layer(path: str, target_crs) -> gpd.GeoDataFrame:
    layer = gpd.read_file(path)
    if layer.crs is None:
        # Asumimos WGS84 si no hay CRS
        layer.set_crs(epsg=4326, inplace=True)
    return layer.to_crs(target_crs)

def distance_to_lines(point_gdf: gpd.GeoDataFrame, lines_gdf: gpd.GeoDataFrame) -> float:
    # calcula distancia mínima (en unidades del CRS)
    p = point_gdf.geometry.iloc[0]
    distances = lines_gdf.distance(p)
    return float(distances.min()) if len(distances) else float("nan")

def point_intersects_polygons(point_gdf: gpd.GeoDataFrame, polys_gdf: gpd.GeoDataFrame) -> bool:
    p = point_gdf.geometry.iloc[0]
    return bool(polys_gdf.intersects(p).any()) if len(polys_gdf) else False

def risk_from_distance(d_m: float, thresholds: dict) -> str:
    if pd.isna(d_m):
        return "Desconocido"
    alto = thresholds.get("alto", 100)
    medio = thresholds.get("medio", 500)
    if d_m < alto:
        return "Alto"
    elif d_m < medio:
        return "Medio"
    else:
        return "Bajo"

def analyze_project(project_row: gpd.GeoDataFrame, layers: dict, rules: dict) -> dict:
    # project_row: GeoDataFrame de 1 fila (un sondeo)
    proj_metric = _to_metric(project_row)
    target_crs = proj_metric.crs

    rivers = load_layer(layers["rivers"], target_crs)
    natura = load_layer(layers["natura"], target_crs)

    # Distancia a cauces
    d_m = distance_to_lines(proj_metric, rivers)
    risk_h = risk_from_distance(d_m, rules.get("hidrologia", {}).get("distancia_rio_m", {}))

    # Intersección Natura
    in_nat = point_intersects_polygons(proj_metric, natura)
    risk_b = (rules.get("biotico", {}).get("natura_intersecta", {}).get("verdadero", "Muy Alto") 
              if in_nat else
              rules.get("biotico", {}).get("natura_intersecta", {}).get("falso", "Bajo"))

    return {
        "id": project_row["id"].iloc[0],
        "lon": project_row["lon"].iloc[0],
        "lat": project_row["lat"].iloc[0],
        "parcela_superficie_m2": project_row["parcela_superficie_m2"].iloc[0],
        "uso_previsto": project_row["uso_previsto"].iloc[0],
        "profundidad_m": project_row["profundidad_m"].iloc[0],
        "caudal_l_s": project_row["caudal_l_s"].iloc[0],
        "distancia_cauce_m": round(d_m, 1) if isinstance(d_m, (int,float)) else None,
        "riesgo_hidrologico": risk_h,
        "en_red_natura": in_nat,
        "riesgo_biotico": risk_b
    }
