
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

EXPECTED_COLS = ["id","lon","lat","parcela_superficie_m2","uso_previsto","profundidad_m","caudal_l_s"]

def load_projects_csv(path: str) -> gpd.GeoDataFrame:
    df = pd.read_csv(path)
    missing = [c for c in EXPECTED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas en {path}: {missing}. Esperadas: {EXPECTED_COLS}")
    gdf = gpd.GeoDataFrame(
        df,
        geometry=[Point(xy) for xy in zip(df["lon"], df["lat"])],
        crs="EPSG:4326"
    )
    return gdf
