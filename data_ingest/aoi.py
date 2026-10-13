"""
aoi.py — Definición del Área de Interés (AOI).

Un `AreaOfInterest` encapsula el recorte geográfico que el usuario analiza:
 bounding box WGS84, geometría `ee.Geometry` equivalente y resolución de trabajo.
El registro de zonas cubre la provincia de Camaná (Arequipa) con sus 8
distritos oficiales (ríos Camaná–Majes, Ocoña y Quilca); cualquier otra
zona puede analizarse mediante coordenadas personalizadas (parse_bbox_text).
"""

from __future__ import annotations

from dataclasses import dataclass

from hidroalert.data_ingest.gee_client import get_ee


@dataclass(frozen=True)
class AreaOfInterest:
    """
    Área de interés rectangular en WGS84.

    Atributos:
        name:     nombre descriptivo (distrito, cuenca, quebrada).
        min_lon, min_lat, max_lon, max_lat: límites del rectángulo.
        scale_m:  resolución de trabajo en metros (30 m por defecto).
    """

    name: str
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float
    scale_m: float = 30.0

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        """Tupla (min_lon, min_lat, max_lon, max_lat)."""
        return (self.min_lon, self.min_lat, self.max_lon, self.max_lat)

    def to_ee_geometry(self):
        """Convierte el AOI a `ee.Geometry.Rectangle` (requiere GEE inicializado)."""
        ee = get_ee()
        return ee.Geometry.Rectangle([self.min_lon, self.min_lat, self.max_lon, self.max_lat])

    @property
    def diagonal_km(self) -> float:
        """Longitud aproximada de la diagonal del AOI en km (aprox. esférica)."""
        import math

        dlon = (self.max_lon - self.min_lon) * 111.32 * math.cos(
            math.radians((self.min_lat + self.max_lat) / 2)
        )
        dlat = (self.max_lat - self.min_lat) * 110.57
        return math.hypot(dlon, dlat)


# ---------------------------------------------------------------------------
# Registro de zonas de análisis (análisis multi-zona)
#
# FOCO: la provincia de CAMANÁ (Arequipa) y sus 8 distritos oficiales
# (ubigeo 0402xx): Camaná, José María Quimper, Mariano Nicolás Valcárcel,
# Mariscal Cáceres, Nicolás de Piérola, Ocoña, Quilca y Samuel Pastor.
# Sistemas fluviales: Majes–Camaná, Ocoña (sector Anchalo) y Quilca.
# Los bboxes son aproximados por zona; la escala de trabajo es de 100 m
# (análisis distrital).
#
# El usuario también puede analizar cualquier otra zona mediante coordenadas
# personalizadas (parse_bbox_text).
# ---------------------------------------------------------------------------
_ZONE_SCALE_M = 100.0  # resolución de trabajo para distritos completos

ZONE_PRESETS: dict[str, AreaOfInterest] = {
    # ---------- Provincia de CAMANÁ (Arequipa) — 8 distritos ----------
    # Distritos oficiales (ubigeo 0402xx): Camaná, José María Quimper,
    # Mariano Nicolás Valcárcel, Mariscal Cáceres, Nicolás de Piérola,
    # Ocoña, Quilca y Samuel Pastor. Sistemas fluviales: Majes–Camaná,
    # Ocoña (sector Anchalo, desborde 02/2025) y Quilca. Los bboxes son
    # referenciales (capital distrital + valle circundante).
    "camana-camana": AreaOfInterest(
        name="Camaná — Distrito de Camaná (valle bajo río Camaná)",
        min_lon=-72.85, min_lat=-16.72, max_lon=-72.60, max_lat=-16.55,
        scale_m=_ZONE_SCALE_M,
    ),
    "camana-quimper": AreaOfInterest(
        name="Camaná — Dto. José María Quimper (El Cardo)",
        min_lon=-72.85, min_lat=-16.70, max_lon=-72.60, max_lat=-16.55,
        scale_m=_ZONE_SCALE_M,
    ),
    "camana-valcarcel": AreaOfInterest(
        name="Camaná — Dto. Mariano Nicolás Valcárcel (Urasqui)",
        min_lon=-73.30, min_lat=-16.10, max_lon=-73.05, max_lat=-15.90,
        scale_m=_ZONE_SCALE_M,
    ),
    "camana-mcaceres": AreaOfInterest(
        name="Camaná — Dto. Mariscal Cáceres (San José)",
        min_lon=-72.85, min_lat=-16.72, max_lon=-72.60, max_lat=-16.55,
        scale_m=_ZONE_SCALE_M,
    ),
    "camana-pierola": AreaOfInterest(
        name="Camaná — Dto. Nicolás de Piérola (San Gregorio)",
        min_lon=-72.85, min_lat=-16.70, max_lon=-72.60, max_lat=-16.52,
        scale_m=_ZONE_SCALE_M,
    ),
    "camana-ocona": AreaOfInterest(
        name="Camaná — Dto. de Ocoña (río Ocoña)",
        min_lon=-73.25, min_lat=-16.55, max_lon=-73.00, max_lat=-16.35,
        scale_m=_ZONE_SCALE_M,
    ),
    "camana-quilca": AreaOfInterest(
        name="Camaná — Dto. de Quilca (bahía de Quilca)",
        min_lon=-72.60, min_lat=-16.85, max_lon=-72.30, max_lat=-16.62,
        scale_m=_ZONE_SCALE_M,
    ),
    "camana-spastor": AreaOfInterest(
        name="Camaná — Dto. Samuel Pastor (La Pampa)",
        min_lon=-72.85, min_lat=-16.70, max_lon=-72.65, max_lat=-16.52,
        scale_m=_ZONE_SCALE_M,
    ),
}

# AOI por defecto: distrito de Camaná, capital de la provincia (valle bajo
# del río Camaná–Majes; crecidas estivales, desbordes 02/2025 en el litoral).
DEFAULT_AOI = ZONE_PRESETS["camana-camana"]


def list_zones() -> list[dict]:
    """Catálogo de zonas para los selectores de la UI (dashboard y mando 3D)."""
    return [
        {"id": zid, "name": aoi.name, "bbox": list(aoi.bbox)}
        for zid, aoi in ZONE_PRESETS.items()
    ]


def get_zone(zone_id: str | None) -> AreaOfInterest | None:
    """Resuelve un id de zona del registro; None si no existe o es vacío."""
    if not zone_id:
        return None
    return ZONE_PRESETS.get(zone_id.strip().lower())


def resolve_aoi(key: str | None) -> AreaOfInterest:
    """
    Resuelve un AreaOfInterest a partir de un id de zona del registro o de
    un bbox "min_lon,min_lat,max_lon,max_lat". Cae en DEFAULT_AOI si key es
    vacío/None (comportamiento histórico intacto).
    """
    if not key:
        return DEFAULT_AOI
    zone = get_zone(key)
    if zone is not None:
        return zone
    return parse_bbox_text(key)


def parse_bbox_text(text: str) -> AreaOfInterest:
    """
    Construye un AOI desde texto "min_lon,min_lat,max_lon,max_lat" (WGS84).

    Lanza ValueError si el formato o el orden de coordenadas es inválido.
    """
    parts = [p.strip() for p in text.split(",")]
    if len(parts) != 4:
        raise ValueError("Formato esperado: min_lon,min_lat,max_lon,max_lat")
    try:
        min_lon, min_lat, max_lon, max_lat = (float(p) for p in parts)
    except ValueError as exc:
        raise ValueError("Las coordenadas deben ser números decimales") from exc
    if min_lon >= max_lon or min_lat >= max_lat:
        raise ValueError("Las coordenadas deben cumplir min < max en ambos ejes")
    if not (-180 <= min_lon < max_lon <= 180 and -90 <= min_lat < max_lat <= 90):
        raise ValueError("Coordenadas fuera de rango WGS84")
    return AreaOfInterest(
        name="AOI personalizado", min_lon=min_lon, min_lat=min_lat, max_lon=max_lon, max_lat=max_lat
    )
