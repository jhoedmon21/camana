"""
buildings_roads.py — Infraestructura expuesta: edificios y vías (Módulo 1).

Usa Google Open Buildings V3 (polígonos de huellas de construcciones) y
GRIP4 (vías globales) desde Earth Engine. Ambas capas se devuelven como
GeoJSON ligero, listo para intersección vectorial en el motor de simulación.

Estas mismas colecciones son las que emplea el workflow de referencia
"satellite-buildings-and-deforestation-detection", por lo que el cruce
SAR + óptica + construcciones queda alineado con ese pipeline.
"""

from __future__ import annotations

import logging
from typing import Any

from hidroalert.data_ingest.gee_client import get_ee
from hidroalert.data_ingest.aoi import AreaOfInterest
from hidroalert.config import CONFIG

logger = logging.getLogger(__name__)

# Límite defensivo de features a descargar (evita respuestas gigantes)
MAX_BUILDINGS = 2000
MAX_ROAD_SEGMENTS = 500


def _fc_to_geojson(fc, max_features: int) -> dict[str, Any]:
    """Descarga una FeatureCollection de GEE como GeoJSON dict (con límite)."""
    ee = get_ee()
    limited = fc.limit(max_features)
    geojson = limited.getInfo()
    # Normaliza a FeatureCollection estándar
    if geojson.get("type") != "FeatureCollection":
        geojson = {
            "type": "FeatureCollection",
            "features": [geojson] if geojson.get("type") else [],
        }
    return geojson


def fetch_buildings(aoi: AreaOfInterest) -> dict[str, Any]:
    """
    Descarga huellas de edificios del AOI.

    Fuente principal: MS Building Footprints — Perú (sat-io), verificada en
    el catálogo de GEE y con excelente cobertura en los Andes. Si falla,
    intenta Google Open Buildings V3 (dataset_alt).

    Returns:
        GeoJSON FeatureCollection. Si no hay edificios mapeados en el AOI
        (común en zonas rurales), devuelve una colección vacía.
    """
    ee = get_ee()
    geom = aoi.to_ee_geometry()
    last_err: Exception | None = None
    for dataset in (CONFIG.gee.buildings_dataset, CONFIG.gee.buildings_dataset_alt):
        try:
            buildings = ee.FeatureCollection(dataset).filterBounds(geom)
            n = buildings.size().getInfo()
            if n == 0:
                logger.warning("Sin edificios en el AOI %s (%s)", aoi.name, dataset)
                return {"type": "FeatureCollection", "features": []}
            logger.info("Edificios (%s): %d en %s", dataset.split("/")[-1], n, aoi.name)
            return _fc_to_geojson(buildings, MAX_BUILDINGS)
        except Exception as exc:  # dataset ausente o sin permisos: prueba el siguiente
            logger.warning("Dataset de edificios no disponible (%s): %s", dataset, exc)
            last_err = exc
    raise RuntimeError(f"Ningún dataset de edificios disponible: {last_err}")


def fetch_roads(aoi: AreaOfInterest) -> dict[str, Any]:
    """
    Descarga vías del AOI (GRIP4 — Global Roads Inventory Project).

    Returns:
        GeoJSON FeatureCollection de líneas; vacía si la capa no cubre el AOI.
    """
    ee = get_ee()
    geom = aoi.to_ee_geometry()
    try:
        roads = ee.FeatureCollection(CONFIG.gee.roads_dataset).filterBounds(geom)
        n = roads.size().getInfo()
    except Exception as exc:  # la capa GRIP4 es comunitaria; puede fallar
        logger.warning("GRIP4 no disponible (%s); se continúa sin vías", exc)
        return {"type": "FeatureCollection", "features": []}
    if n == 0:
        return {"type": "FeatureCollection", "features": []}
    return _fc_to_geojson(roads, MAX_ROAD_SEGMENTS)


def fetch_farmland(aoi: AreaOfInterest) -> dict[str, Any] | None:
    """
    Descarga suelo agrícola del AOI (ESA WorldCover, clase 'cultivated').

    Convierte el ráster de 10 m a polígonos para poder intersectar con la
    lámina de agua simulada. Devuelve None si no hay suelo agrícola.
    """
    ee = get_ee()
    geom = aoi.to_ee_geometry()
    worldcover = (
        ee.ImageCollection("ESA/WorldCover/v200")
        .first()
        .select("Map")
    )
    cultivated = worldcover.eq(40)  # 40 = 'Cropland' en la leyenda WorldCover
    vectors = cultivated.selfMask().reduceToVectors(
        geometry=geom,
        scale=aoi.scale_m,
        geometryType="polygon",
        eightConnected=True,
        maxPixels=1e10,
        bestEffort=True,
    )
    n = vectors.size().getInfo()
    if n == 0:
        return None
    return _fc_to_geojson(vectors, 200)
