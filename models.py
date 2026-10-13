"""
Dataclasses del dominio hidrológico de HidroAlert.

Estas estructuras viajan entre módulos: el motor de ingestión (Módulo 1)
produce un `AreaSnapshot`, la simulación (Módulo 2) lo consume y produce
`SimulationResult`, y las alertas (Módulo 4) serializan `SimulationResult`
a JSON para los informes.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Literal

import numpy as np

# Niveles de alerta del sistema
AlertLevel = Literal["VERDE", "AMARILLO", "ROJO"]


@dataclass
class AreaSnapshot:
    """
    Contexto geográfico de un área de análisis (Módulo 1).

    Contiene la información satelital e hidrológica ya extraída de Earth Engine
    (o de fuentes locales en modo demo), lista para el motor de simulación.

    Atributos:
        aoi_name:           Nombre descriptivo del área (ej. distrito, cuenca).
        bbox:               (min_lon, min_lat, max_lon, max_lat) del área.
        hand:               Matriz 2D HAND (m sobre el drenaje más cercano). NaN fuera.
        dem:                Matriz 2D de elevación (m). NaN fuera.
        flood_mask_observed: Máscara booleana de agua observada por Sentinel-1 (Otsu+HAND).
        buildings:          GeoJSON FeatureCollection de edificios (Open Buildings).
        roads:              GeoJSON FeatureCollection de vías (GRIP4) [opcional].
        farmland_polygon:   GeoJSON Polygon/MultiPolygon de suelo agrícola [opcional].
        cell_area_m2:       Área de celda del ráster (m²) para cálculo de volumen.
        observed_water_area_m2: Área inundada observada por SAR (m²).
    """

    aoi_name: str
    bbox: tuple[float, float, float, float]
    hand: np.ndarray
    dem: np.ndarray
    cell_area_m2: float
    upa: np.ndarray | None = None   # área upstream MERIT 'upa' (km²) — red de drenaje
    flood_mask_observed: np.ndarray | None = None
    buildings: dict[str, Any] | None = None
    roads: dict[str, Any] | None = None
    farmland_polygon: dict[str, Any] | None = None
    observed_water_area_m2: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialización resumida para JSON (sin matrices NumPy)."""
        return {
            "aoi_name": self.aoi_name,
            "bbox": list(self.bbox),
            "cell_area_m2": self.cell_area_m2,
            "observed_water_area_m2": self.observed_water_area_m2,
            "n_buildings": _count_features(self.buildings),
            "n_roads": _count_features(self.roads),
            "has_farmland": self.farmland_polygon is not None,
        }


def _count_features(fc: dict[str, Any] | None) -> int:
    """Cuenta features de una FeatureCollection GeoJSON (0 si es None)."""
    if not fc:
        return 0
    return len(fc.get("features", []))


@dataclass
class BuildingImpact:
    """Impacto sobre una edificación individual (Módulo 2)."""

    building_id: str | None
    depth_m: float          # profundidad media de agua sobre el edificio (m)
    centroid: tuple[float, float]  # (lon, lat) del centroide


@dataclass
class RoadImpact:
    """Impacto sobre una vía (Módulo 2)."""

    road_id: str | None
    blocked: bool           # True si algún punto de la vía queda bajo agua > 0.2 m
    max_depth_m: float


@dataclass
class ImpactMatrix:
    """
    Matriz de efectos e impacto estimado (Módulo 2, entregable 3).

    Resume las consecuencias del escenario simulado sobre la infraestructura:
    viviendas afectadas, vías bloqueadas, hectáreas agrícolas sumergidas.
    """

    buildings_affected: int = 0
    buildings_total: int = 0
    buildings_detail: list[BuildingImpact] = field(default_factory=list)
    roads_blocked: int = 0
    roads_total: int = 0
    roads_detail: list[RoadImpact] = field(default_factory=list)
    farmland_flooded_ha: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Versión serializable para JSON (sin objetos anidados complejos)."""
        return {
            "buildings_affected": self.buildings_affected,
            "buildings_total": self.buildings_total,
            "roads_blocked": self.roads_blocked,
            "roads_total": self.roads_total,
            "farmland_flooded_ha": round(self.farmland_flooded_ha, 2),
            "buildings_detail": [
                {
                    "building_id": b.building_id,
                    "depth_m": round(b.depth_m, 3),
                    "centroid": list(b.centroid),
                }
                for b in self.buildings_detail
            ],
            "roads_detail": [
                {
                    "road_id": r.road_id,
                    "blocked": r.blocked,
                    "max_depth_m": round(r.max_depth_m, 3),
                }
                for r in self.roads_detail
            ],
        }


@dataclass
class SimulationResult:
    """
    Resultado completo de una simulación hidrológica (Módulo 2).

    Es el objeto central que consumen el dashboard (Módulo 3) y el motor
    de alertas (Módulo 4).
    """

    aoi_name: str
    bbox: tuple[float, float, float, float]
    # Parámetros del escenario
    precipitation_mm_h: float
    flow_increase_pct: float
    # Hidráulica
    depth_m: np.ndarray                    # lámina de agua por celda (m)
    flood_mask: np.ndarray                 # True donde hay agua superficial
    water_volume_m3: float                 # volumen total desbordado/acumulado (m³)
    water_volume_lits: float               # equivalente en litros
    flooded_area_m2: float                 # área inundada simulada (m²)
    # Impacto
    impact: ImpactMatrix
    # Observación satelital de referencia (si hubo)
    observed_water_area_m2: float = 0.0
    # Concentración de agua sobre terreno (escorrentía superficial D8).
    # overland_depth_m es None cuando la opción no se simuló; los demás
    # campos quedan en 0 (los stats usan el mismo corte de 1 cm del motor).
    overland_depth_m: np.ndarray | None = None
    overland_volume_m3: float = 0.0
    overland_area_m2: float = 0.0
    overland_max_depth_m: float = 0.0
    # Metadatos
    scenario_label: str = ""
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialización JSON completa (matrices excluidas por tamaño)."""
        return {
            "aoi_name": self.aoi_name,
            "bbox": list(self.bbox),
            "scenario": {
                "precipitation_mm_h": self.precipitation_mm_h,
                "flow_increase_pct": self.flow_increase_pct,
                "label": self.scenario_label,
            },
            "hydrology": {
                "water_volume_m3": round(self.water_volume_m3, 1),
                "water_volume_lits": round(self.water_volume_lits, 1),
                "water_volume_thousand_lits": round(self.water_volume_lits / 1000, 1),
                "flooded_area_m2": round(self.flooded_area_m2, 1),
                "flooded_area_ha": round(self.flooded_area_m2 / 10_000, 2),
                "max_depth_m": round(float(np.nanmax(self.depth_m)), 3)
                if self.flood_mask.any()
                else 0.0,
                "overland_included": self.overland_depth_m is not None,
                "overland_volume_m3": round(self.overland_volume_m3, 1),
                "overland_area_ha": round(self.overland_area_m2 / 10_000, 2),
                "overland_max_depth_m": round(self.overland_max_depth_m, 3),
            },
            "impact": self.impact.to_dict(),
            "observed_water_area_m2": round(self.observed_water_area_m2, 1),
            "timestamp": self.timestamp,
        }


@dataclass
class AlertDecision:
    """Salida del motor de alertas condicionales (Módulo 4)."""

    level: AlertLevel
    reasons: list[str] = field(default_factory=list)
    thresholds_used: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "reasons": self.reasons,
            "thresholds": self.thresholds_used,
        }
