"""
precipitation.py — Precipitación observada por satélite (IMERG / GPM).

Fuente de lluvia REAL que alimenta el motor de simulación, en el espíritu
de WeatherNext 3: usar observaciones satelitales recientes en lugar de un
valor manual ciego.

* IMERG V07 (NASA GPM): imágenes semihorarias ~10 km, banda
  'precipitation' en mm/h — disponible en Earth Engine (verificada en el
  proyecto `egresados-q9tr`).
* `observed_precipitation_mm_h()` entrega la lluvia representativa del AOI
  en las últimas N horas (peor media móvil 1h por defecto).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from hidroalert.data_ingest.gee_client import get_ee
from hidroalert.data_ingest.aoi import AreaOfInterest

logger = logging.getLogger(__name__)

# Colección confirmada en el catálogo del proyecto (V07, semihoraria)
IMERG_COLLECTION = "NASA/GPM_L3/IMERG_V07"
PRECIP_BAND = "precipitation"  # mm/hr
# Escala nativa de IMERG ~0.1° (~11 km); usarla evita sobremuestreo costoso
IMERG_SCALE_M = 11_132


def observed_precipitation_mm_h(
    aoi: AreaOfInterest,
    hours: int = 6,
    mode: str = "max",
) -> dict:
    """
    Lluvia observada por IMERG sobre el AOI en las últimas `hours` horas.

    Args:
        aoi:   área de interés.
        hours: ventana de observación hacia atrás (default 6 h).
        mode:  'max'  → peor media espacial 1h del periodo (conservador,
                       recomendado para alertas);
               'mean' → media del periodo (carácter general del evento).

    Returns:
        dict con:
            mm_h (float):    intensidad de lluvia observada (mm/h).
            mode, hours:     parámetros de la consulta.
            images (int):    imágenes IMERG usadas.
            source (str):    colección GEE de origen.
            end (str):       timestamp UTC del final de la ventana.
    """
    ee = get_ee()
    full = ee.ImageCollection(IMERG_COLLECTION)
    geom = aoi.to_ee_geometry()

    # La ingesta de IMERG en GEE tiene latencia variable (4–48 h): la ventana
    # se ancla a la ÚLTIMA imagen disponible en lugar del reloj actual.
    last_ms = full.sort("system:time_start", False).first().get("system:time_start").getInfo()
    end = datetime.fromtimestamp(last_ms / 1000, tz=timezone.utc)
    start = end - timedelta(hours=hours)

    col = (
        full.filterDate(start, end)
        .filterBounds(geom)
        .select(PRECIP_BAND)
    )
    n = col.size().getInfo()
    if n == 0:
        raise RuntimeError(
            f"Sin imágenes IMERG en las últimas {hours} h para {aoi.name}."
        )

    if mode == "mean":
        stat = (
            col.mean()
            .reduceRegion(
                reducer=ee.Reducer.mean(),
                geometry=geom,
                scale=IMERG_SCALE_M,
                maxPixels=1e9,
            )
            .get(PRECIP_BAND)
        )
        value = float(stat.getInfo())
    else:  # 'max': media espacial por imagen (≈1 h) y se toma la peor
        def _img_mean(img):
            return img.set(
                "mmh",
                img.reduceRegion(
                    reducer=ee.Reducer.mean(),
                    geometry=geom,
                    scale=IMERG_SCALE_M,
                    maxPixels=1e9,
                ).get(PRECIP_BAND),
            )

        stats = col.map(_img_mean)
        value = float(stats.aggregate_max("mmh").getInfo())

    logger.info("IMERG %s: %.2f mm/h (%d imágenes, %d h, modo %s)",
                aoi.name, value, n, hours, mode)
    return {
        "mm_h": value,
        "mode": mode,
        "hours": hours,
        "images": n,
        "source": IMERG_COLLECTION,
        "end": end.isoformat(),
    }
