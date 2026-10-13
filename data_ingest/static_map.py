"""
static_map.py — Recortes de mapa vía Google Maps Static API (Módulo 1).

Genera la imagen del "mapa estático recortado de la zona de desastre" que
adjunta el informe de alerta (Módulo 4). Si no hay API key configurada,
devuelve None y los informes usan el render local (matplotlib/folium).
"""

from __future__ import annotations

import logging
from pathlib import Path

import requests

from hidroalert.config import CONFIG, REPORTS_DIR

logger = logging.getLogger(__name__)

STATIC_MAP_URL = "https://maps.googleapis.com/maps/api/staticmap"


def fetch_static_map_png(
    center_lat: float,
    center_lon: float,
    zoom: int = 15,
    size_px: int = 640,
    maptype: str = "satellite",
    out_path: Path | None = None,
) -> Path | None:
    """
    Descarga un recorte satelital de Google Maps Static API.

    Args:
        center_lat/lon: centro del recorte (WGS84).
        zoom:           nivel de zoom (15 ≈ 1-2 km de ancho).
        size_px:        tamaño cuadrado en píxeles (máx. 640 en plan gratuito).
        maptype:        'satellite' | 'hybrid' | 'terrain' | 'roadmap'.
        out_path:       ruta destino del PNG; si es None se autogenera.

    Returns:
        Ruta del PNG descargado, o None si la API key no está configurada
        o la descarga falla (degradación silenciosa con log).
    """
    if not CONFIG.gmaps.is_configured:
        logger.info("Google Maps Static no configurado; se omite el recorte satelital.")
        return None

    params = {
        "center": f"{center_lat},{center_lon}",
        "zoom": zoom,
        "size": f"{size_px}x{size_px}",
        "maptype": maptype,
        "key": CONFIG.gmaps.api_key,
    }
    try:
        resp = requests.get(STATIC_MAP_URL, params=params, timeout=20)
        resp.raise_for_status()
        if not resp.content.startswith(b"\x89PNG"):
            logger.warning("Maps Static devolvió contenido no PNG (¿error de key?)")
            return None
        if out_path is None:
            out_path = REPORTS_DIR / f"static_map_{center_lat:.4f}_{center_lon:.4f}.png"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(resp.content)
        logger.info("Mapa estático guardado en %s", out_path)
        return out_path
    except requests.RequestException as exc:
        logger.warning("Fallo descargando mapa estático: %s", exc)
        return None
