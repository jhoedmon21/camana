"""
sar_flood.py — Detección de inundaciones con Sentinel-1 GRD (Módulo 1).

Pipeline (referencia: workflows de cambio de retrodispersión SAR):
    1. Filtra la colección Sentinel-1 GRD por AOI, órbita y polarización (VV/VH).
    2. Convierte a dB y calcula el ratio VH/VV para robustez frente a textura.
    3. Aplica el filtro suavizado (radio de speckle) y el umbral de Otsu
       global para separar agua (baja retrodispersión) de tierra.
    4. Restringe la detección con la máscara HAND (Height Above Nearest
       Drainage): solo se acepta "agua" en celdas con HAND bajo, eliminando
       falsos positivos de sombra radar y superficies lisas permanentes.
    5. Exporta la máscara observada como matriz NumPy para el motor de
       simulación, junto con el área de agua observada en m².
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import numpy as np

from hidroalert.data_ingest.gee_client import get_ee
from hidroalert.data_ingest.aoi import AreaOfInterest

logger = logging.getLogger(__name__)

# Ventana de días hacia atrás para buscar imágenes Sentinel-1
DEFAULT_LOOKBACK_DAYS = 12


def _sentinel1_collection(aoi: AreaOfInterest, lookback_days: int, orbit: str | None):
    """Construye la colección Sentinel-1 GRD filtrada por AOI y fecha."""
    ee = get_ee()
    end = datetime.utcnow()
    start = end - timedelta(days=lookback_days)
    col = (
        ee.ImageCollection("COPERNICUS/S1_GRD")
        .filterBounds(aoi.to_ee_geometry())
        .filterDate(start, end)
        # IW (Interferometric Wide) es el modo estándar para inundaciones
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
        .filter(ee.Filter.eq("instrumentMode", "IW"))
    )
    if orbit:
        # 'ASCENDING' o 'DESCENDING': fija la geometría para comparar pases
        col = col.filter(ee.Filter.eq("orbitProperties_pass", orbit))
    return col, start, end


def _to_db(image):
    """Añade el ratio VH/VV (dB). Las bandas VV/VH de S1_GRD ya están en dB."""
    ee = get_ee()
    vv = image.select("VV")
    vh = image.select("VH")
    ratio = vh.subtract(vv).rename("VHVV")  # ratio VH/VV en dB: discrimina agua lisa
    return vv.addBands(vh).addBands(ratio).copyProperties(image, image.propertyNames())


def _otsu_threshold(hist_computed) -> float:
    """
    Calcula el umbral de Otsu a partir de un histograma `ee.Reducer.histogram`.

    Args:
        hist_computed: objeto computado de GEE (resultado de
            `reduceRegion(...).get(banda)`); se evalúa con `.getInfo()` y
            produce {"bucketMeans": [...], "histogram": [...]}.

    Implementación vectorizada: recorre los centros de bin y maximiza la
    varianza entre clases (agua vs. tierra) según el clásico método de Otsu.
    """
    data = hist_computed.getInfo()
    means = np.asarray(data.get("bucketMeans", []), dtype=float)
    counts = np.asarray(data.get("histogram", []), dtype=float)
    if means.size < 2:
        return float("nan")

    # Probabilidades acumuladas y medias acumuladas
    total = counts.sum()
    if total <= 0:
        return float("nan")
    w0 = np.cumsum(counts)[:-1] / total                 # peso clase 0 (agua)
    w1 = 1.0 - w0                                       # peso clase 1 (tierra)
    sum_total = (counts * means).sum()
    sum0 = np.cumsum(counts * means)[:-1]
    mu0 = np.divide(sum0, w0, out=np.zeros_like(sum0), where=w0 > 0)
    mu1 = np.divide(sum_total - sum0, w1, out=np.zeros_like(w1), where=w1 > 0)
    between_var = w0 * w1 * (mu0 - mu1) ** 2
    idx = int(np.nanargmax(between_var))
    return float(means[idx])


def detect_observed_flood(
    aoi: AreaOfInterest,
    lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    orbit: str | None = None,
    hand_max_m: float = 15.0,
    min_water_pixels: int = 5,
) -> dict:
    """
    Ejecuta el pipeline SAR y devuelve el agua observada para el AOI.

    Args:
        aoi:              área de interés.
        lookback_days:    ventana temporal de búsqueda de imágenes.
        orbit:            'ASCENDING' | 'DESCENDING' | None (todas).
        hand_max_m:       HAND máximo para aceptar un píxel como inundación.
        min_water_pixels: mínimo de píxeles de agua para considerar el evento.

    Returns:
        dict con:
            mask (np.ndarray bool): píxeles de agua observada (NaN-free).
            hand (np.ndarray):      matriz HAND del AOI (NaN fuera del AOI).
            dem (np.ndarray):       matriz DEM del AOI.
            cell_area_m2 (float):   área del píxel en m².
            water_area_m2 (float):  área de agua observada.
            image_id (str):         imagen Sentinel-1 usada.
            date (str):             fecha ISO de la imagen.
            threshold_db (float):   umbral de Otsu en dB.
            stats (dict):           contadores de depuración.
    """
    ee = get_ee()
    geom = aoi.to_ee_geometry()

    col, start, end = _sentinel1_collection(aoi, lookback_days, orbit)
    size = col.size().getInfo()
    if size == 0:
        raise RuntimeError(
            f"Sin imágenes Sentinel-1 en los últimos {lookback_days} días para el AOI."
        )
    col = col.map(_to_db)
    latest = col.sort("system:time_start", False).first()
    image_id = latest.get("system:id").getInfo() or latest.get("system:index").getInfo()
    date = latest.get("system:time_start").getInfo()
    date_iso = datetime.utcfromtimestamp(date / 1000).isoformat()

    # --- Histograma y umbral de Otsu sobre la banda VH (más estable en llanuras)
    hist_reducer = ee.Reducer.histogram(255, 0.1)
    hist = latest.select("VH").reduceRegion(
        reducer=hist_reducer,
        geometry=geom,
        scale=aoi.scale_m,
        maxPixels=1e10,
        bestEffort=True,
    )
    threshold_db = _otsu_threshold(hist.get("VH"))

    # --- Máscara de agua por Otsu (retrodispersión por debajo del umbral)
    water_otsu = latest.select("VH").lt(threshold_db)

    # --- Filtro HAND: elimina sombras radar en laderas (HAND alto)
    # MERIT Hydro: bandas [elv, dir, wth, wat, upa, upg, hnd, viswth]
    merit = ee.Image("MERIT/Hydro/v1_0_1")
    hand_img = merit.select("hnd")          # Height Above Nearest Drainage (m)
    hand_low = hand_img.lte(hand_max_m)
    water = water_otsu.And(hand_low)

    # --- Elevación y red de drenaje del mismo dataset (grids alineados)
    dem_img = merit.select("elv")
    upa_img = merit.select("upa")           # área upstream (km²) → red de drenaje

    # --- Muestreo a NumPy con CRS/scale comunes (grillas idénticas)
    region = geom.bounds(maxError=1)
    common = {"crs": "EPSG:4326", "scale": aoi.scale_m}
    flood_np = _sample_to_numpy(water.unmask(0).toByte(), region, aoi.scale_m, common["crs"])
    hand_np = _sample_to_numpy(hand_img.unmask(-9999), region, aoi.scale_m, common["crs"])
    dem_np = _sample_to_numpy(dem_img.unmask(-9999), region, aoi.scale_m, common["crs"])
    try:
        upa_np = _sample_to_numpy(upa_img.unmask(-9999), region, aoi.scale_m, common["crs"])
        upa_np = np.where(upa_np == -9999, np.nan, upa_np)
    except Exception as exc:  # banda opcional: sin ella no hay capa de drenaje
        logger.warning("No se pudo muestrear la red de drenaje (upa): %s", exc)
        upa_np = None

    # Alineación defensiva: recorta al tamaño común si algún grid difiere
    hmin = min(flood_np.shape[0], hand_np.shape[0], dem_np.shape[0])
    wmin = min(flood_np.shape[1], hand_np.shape[1], dem_np.shape[1])
    flood_np = flood_np[:hmin, :wmin]
    hand_np = hand_np[:hmin, :wmin]
    dem_np = dem_np[:hmin, :wmin]

    hand_np = np.where(hand_np == -9999, np.nan, hand_np)
    dem_np = np.where(dem_np == -9999, np.nan, dem_np)
    mask = flood_np.astype(bool)
    mask &= ~np.isnan(hand_np)

    cell_area_m2 = aoi.scale_m ** 2
    water_area = float(mask.sum() * cell_area_m2)

    return {
        "mask": mask,
        "hand": hand_np,
        "dem": dem_np,
        "upa": upa_np,
        "cell_area_m2": cell_area_m2,
        "water_area_m2": water_area,
        "image_id": image_id,
        "date": date_iso,
        "threshold_db": threshold_db,
        "stats": {
            "images_in_collection": size,
            "valid_pixels": int((~np.isnan(hand_np)).sum()),
            "water_pixels": int(mask.sum()),
            "min_water_pixels": min_water_pixels,
        },
    }


def _sample_to_numpy(image, region, scale_m: float, crs: str = "EPSG:4326") -> np.ndarray:
    """
    Descarga un ráster de Earth Engine como matriz NumPy vía `getDownloadURL`.

    Se fuerza `crs` y `scale` explícitos para que varias imágenes (S1 en UTM,
    MERIT en 4326) produzcan grillas idénticas y comparables celda a celda.
    El formato NPY es compatible con todas las versiones modernas del API.
    """
    import io

    import requests

    url = image.getDownloadURL(
        {"scale": scale_m, "region": region, "crs": crs, "format": "NPY"}
    )
    response = requests.get(url, timeout=120)
    response.raise_for_status()
    array = np.load(io.BytesIO(response.content), allow_pickle=False)
    # El NPY contiene un array estructurado con una banda por campo
    if array.dtype.names:
        array = array[array.dtype.names[0]]
    return np.asarray(array, dtype=float)
