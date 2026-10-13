"""
ingest_service.py — Orquestador del Módulo 1.

Función de alto nivel `build_area_snapshot()`: ejecuta el pipeline completo
de ingesta (SAR + HAND + DEM + edificios + vías + agricultura) y devuelve un
`AreaSnapshot` listo para el motor de simulación (Módulo 2).

Incluye `build_demo_snapshot()`, que genera un área sintética con la misma
interfaz para poder ejecutar el sistema sin credenciales GEE (demo/offline).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import numpy as np

from hidroalert.data_ingest.gee_client import get_ee
from hidroalert.data_ingest.aoi import AreaOfInterest
from hidroalert.data_ingest.sar_flood import detect_observed_flood
from hidroalert.data_ingest.buildings_roads import (
    fetch_buildings,
    fetch_roads,
    fetch_farmland,
)
from hidroalert.models import AreaSnapshot

logger = logging.getLogger(__name__)


def build_area_snapshot(aoi: AreaOfInterest, lookback_days: int = 12) -> AreaSnapshot:
    """
    Pipeline completo de ingesta satelital para un AOI (Módulo 1).

    Pasos:
        1. Detección SAR de inundación observada (Sentinel-1, Otsu + HAND).
        2. Descarga de matrices HAND y DEM.
        3. Descarga de edificios (Open Buildings), vías (GRIP4) y agricultura.

    Raises:
        RuntimeError: si GEE no está configurado o falla la ingesta.
    """
    get_ee()  # valida credenciales antes de empezar
    logger.info("Ingesta GEE iniciada para %s", aoi.name)

    sar = detect_observed_flood(aoi, lookback_days=lookback_days)

    try:
        buildings = fetch_buildings(aoi)
    except Exception as exc:
        logger.warning("No se pudieron descargar edificios: %s", exc)
        buildings = {"type": "FeatureCollection", "features": []}

    try:
        roads = fetch_roads(aoi)
    except Exception as exc:
        logger.warning("No se pudieron descargar vías: %s", exc)
        roads = {"type": "FeatureCollection", "features": []}

    try:
        farmland = fetch_farmland(aoi)
    except Exception as exc:
        logger.warning("No se pudo descargar agricultura: %s", exc)
        farmland = None

    return AreaSnapshot(
        aoi_name=aoi.name,
        bbox=aoi.bbox,
        hand=sar["hand"],
        dem=sar["dem"],
        cell_area_m2=sar["cell_area_m2"],
        upa=sar.get("upa"),
        flood_mask_observed=sar["mask"],
        buildings=buildings,
        roads=roads,
        farmland_polygon=farmland,
        observed_water_area_m2=sar["water_area_m2"],
    )


def build_demo_snapshot(seed: int = 42) -> AreaSnapshot:
    """
    Snapshot sintético con la misma interfaz que el real (modo demo).

    Genera un valle con un cauce principal (HAND ~0) rodeado de laderas,
    manchas de agua observada cerca del cauce y una malla de edificios
    hipotéticos. Permite probar todo el sistema sin credenciales GEE.
    """
    rng = np.random.default_rng(seed)
    n = 200  # matriz 200x200 => 40 000 celdas de 30 m => ~36 km²
    cell = 30.0

    # Coordenadas geográficas sintéticas alrededor de Lima
    lon0, lat0 = -77.00, -12.00
    dlon = (n * cell) / (111_320 * np.cos(np.radians(lat0)))
    dlat = (n * cell) / 110_570
    bbox = (lon0 - dlon / 2, lat0 - dlat / 2, lon0 + dlon / 2, lat0 + dlat / 2)

    # --- Terreno: valle en "V" con cauce serpenteante
    x = np.arange(n)
    y = np.arange(n)
    xx, yy = np.meshgrid(x, y)
    river_y = (n / 2 + 25 * np.sin(x / 18.0)).astype(int)  # fila del cauce por columna
    dist_to_river = np.abs(yy - river_y[np.newaxis, :])  # distancia en celdas al cauce
    hand = np.clip(dist_to_river * 1.8 + rng.normal(0, 0.6, (n, n)), 0, 60)
    dem = 120 + hand * 0.9 + rng.normal(0, 1.5, (n, n))

    # --- Agua observada por "SAR": celdas con HAND < 3 m cerca del cauce
    flood_mask = (hand < 3.0) & (rng.random((n, n)) > 0.25)

    # --- Edificios sintéticos: asentamientos a ambos márgenes del valle
    # (offsets pequeños: HAND local ≈ 1–3 m ⇒ se inundan en escenarios medios)
    features = []
    bid = 0
    for cx in range(30, n - 30, 12):
        for cy_off in (-4, -2, 2, 4):
            cy = int(river_y[cx] + cy_off)
            if 5 <= cy < n - 5:
                # huella de 3x2 celdas convertida a bbox geográfico
                res_lon = dlon / n
                res_lat = dlat / n
                bx0 = lon0 - dlon / 2 + cx * res_lon
                by0 = lat0 - dlat / 2 + (n - cy) * res_lat  # fila 0 = norte
                features.append(
                    {
                        "type": "Feature",
                        "id": f"demo-bld-{bid}",
                        "properties": {"building_id": f"demo-bld-{bid}"},
                        "geometry": {
                            "type": "Polygon",
                            "coordinates": [
                                [
                                    [bx0, by0],
                                    [bx0 + 2.5 * res_lon, by0],
                                    [bx0 + 2.5 * res_lon, by0 + 2 * res_lat],
                                    [bx0, by0 + 2 * res_lat],
                                    [bx0, by0],
                                ]
                            ],
                        },
                    }
                )
                bid += 1
    buildings = {"type": "FeatureCollection", "features": features}

    # --- Vías sintéticas: una carretera longitudinal junto al cauce
    road_coords = []
    for cx in range(0, n, 10):
        cy = int(river_y[cx] + 6)
        res_lon = dlon / n
        res_lat = dlat / n
        road_coords.append(
            [lon0 - dlon / 2 + cx * res_lon, lat0 - dlat / 2 + (n - cy) * res_lat]
        )
    roads = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "id": "demo-road-0",
                "properties": {"road_id": "Vía Marginal"},
                "geometry": {"type": "LineString", "coordinates": road_coords},
            }
        ],
    }

    # --- Suelo agrícola sintético: parche en la margen izquierda
    farm_x0, farm_x1 = 10, 90
    farm_row = int(river_y[farm_x0]) + 20
    fx0 = lon0 - dlon / 2 + farm_x0 * (dlon / n)
    fx1 = lon0 - dlon / 2 + farm_x1 * (dlon / n)
    fy0 = lat0 - dlat / 2 + (n - farm_row - 15) * (dlat / n)
    fy1 = lat0 - dlat / 2 + (n - farm_row) * (dlat / n)
    farmland = {
        "type": "Feature",
        "properties": {"name": "Valle agrícola demo"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[fx0, fy0], [fx1, fy0], [fx1, fy1], [fx0, fy1], [fx0, fy0]]],
        },
    }

    # Red de drenaje sintética: área upstream crece hacia el cauce principal
    # (distancia lateral al cauce define 'upa' en km², máx ~80 km² en el cauce)
    upa = np.clip(80.0 - dist_to_river * 3.5 + rng.normal(0, 2.0, (n, n)), 0, 120)
    upa = np.where(dist_to_river <= 1, 90.0, upa)  # cauce principal

    return AreaSnapshot(
        aoi_name="Valle Demo (offline)",
        bbox=bbox,
        hand=hand,
        dem=dem,
        cell_area_m2=cell * cell,
        upa=upa,
        flood_mask_observed=flood_mask,
        buildings=buildings,
        roads=roads,
        farmland_polygon=farmland,
        observed_water_area_m2=float(flood_mask.sum() * cell * cell),
    )
