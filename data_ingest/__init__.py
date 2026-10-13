"""Módulo 1 — Ingesta de datos satelitales (GEE Sentinel-1, HAND, edificios, vías)."""

from hidroalert.data_ingest.gee_client import get_ee
from hidroalert.data_ingest.aoi import (
    AreaOfInterest,
    parse_bbox_text,
    DEFAULT_AOI,
    ZONE_PRESETS,
    list_zones,
    get_zone,
    resolve_aoi,
)

__all__ = [
    "get_ee",
    "AreaOfInterest",
    "parse_bbox_text",
    "DEFAULT_AOI",
    "ZONE_PRESETS",
    "list_zones",
    "get_zone",
    "resolve_aoi",
]
