"""
impact.py — Matriz de efectos e impacto estimado (Módulo 2, entregable 3).

Cruza la lámina de agua simulada con las capas vectoriales descargadas por
el Módulo 1:
    * Edificios (Open Buildings): profundidad media sobre cada huella,
      conteo de afectados (> 15 cm).
    * Vías (GRIP4): segmentos bloqueados (lámina > 20 cm en algún vértice).
    * Suelo agrícola (WorldCover 'Cropland'): hectáreas sumergidas
      (intersección aproximada por muestreo de celdas dentro del polígono).
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
from shapely.geometry import shape, Point
from shapely.strtree import STRtree

from hidroalert.models import AreaSnapshot, BuildingImpact, RoadImpact, ImpactMatrix

logger = logging.getLogger(__name__)


def _lonlat_to_indices(
    lon: float,
    lat: float,
    bbox: tuple[float, float, float, float],
    ncols: int,
    nrows: int,
) -> tuple[int, int]:
    """
    Convierte coordenadas geográficas a índices de celda del ráster.

    Fila 0 = norte (convención de rásters), columna 0 = oeste.
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    col = int((lon - min_lon) / (max_lon - min_lon) * ncols)
    row = int((max_lat - lat) / (max_lat - min_lat) * nrows)
    return min(max(col, 0), ncols - 1), min(max(row, 0), nrows - 1)


def compute_impact_matrix(
    snapshot: AreaSnapshot,
    depth_m: np.ndarray,
    flood_mask: np.ndarray,
    bbox: tuple[float, float, float, float],
    cell_area_m2: float,
    building_threshold_m: float = 0.15,
    road_threshold_m: float = 0.20,
    include_farmland: bool = True,
    include_roads: bool = True,
) -> ImpactMatrix:
    """
    Calcula la matriz de impacto del escenario simulado.

    Args:
        snapshot:               contexto del área (edificios, vías, agricultura).
        depth_m:                lámina simulada por celda (m).
        flood_mask:             True donde hay agua.
        bbox:                   extensión geográfica del ráster.
        cell_area_m2:           área de cada celda (m²).
        building_threshold_m:   profundidad que considera "afectado" un edificio.
        road_threshold_m:       profundidad que considera "bloqueada" una vía.
        include_farmland:       False omite la intersección agrícola (costosa;
                            útil en series temporales de 48 h).
        include_roads:          False omite el muestreo de vías (costoso).

    Returns:
        ImpactMatrix con conteos y detalles por elemento expuesto.
    """
    impact = ImpactMatrix(
        buildings_total=len(snapshot.buildings["features"]) if snapshot.buildings else 0,
        roads_total=len(snapshot.roads["features"]) if snapshot.roads else 0,
    )
    nrows, ncols = depth_m.shape

    # ---------------- Edificios ----------------
    if snapshot.buildings:
        # STRtree para buscar celdas cercanas sin O(n·m)
        geoms = []
        for feat in snapshot.buildings["features"]:
            try:
                geoms.append(shape(feat["geometry"]))
            except (KeyError, ValueError):
                continue
        if geoms:
            tree = STRtree(geoms)
            for idx, feat in enumerate(snapshot.buildings["features"]):
                geom = geoms[idx] if idx < len(geoms) else None
                if geom is None or geom.is_empty:
                    continue
                centroid = geom.centroid
                col, row = _lonlat_to_indices(
                    centroid.x, centroid.y, bbox, ncols, nrows
                )
                d = float(depth_m[row, col])
                if d >= building_threshold_m:
                    impact.buildings_affected += 1
                    impact.buildings_detail.append(
                        BuildingImpact(
                            building_id=feat.get("properties", {}).get(
                                "building_id", feat.get("id")
                            ),
                            depth_m=d,
                            centroid=(centroid.x, centroid.y),
                        )
                    )

    # ---------------- Vías ----------------
    if snapshot.roads and include_roads:
        for feat in snapshot.roads["features"]:
            try:
                line = shape(feat["geometry"])
            except (KeyError, ValueError):
                continue
            max_depth = 0.0
            # Muestreo de vértices (y punto medio de cada segmento) sobre la lámina.
            # GRIP4 entrega tanto LineString como MultiLineString: se aplanan todas
            # las partes (las multiparte no tienen .coords propio).
            sample_pts: list[tuple[float, float]] = []
            parts = [line] if line.geom_type == "LineString" else list(getattr(line, "geoms", []) or [])
            for part in parts:
                if part.is_empty or part.geom_type != "LineString":
                    continue
                coords = list(part.coords)
                for i in range(len(coords) - 1):
                    x0, y0 = coords[i]
                    x1, y1 = coords[i + 1]
                    sample_pts.append((x0, y0))
                    sample_pts.append(((x0 + x1) / 2, (y0 + y1) / 2))
                if coords:
                    sample_pts.append(coords[-1])
            for lon, lat in sample_pts:
                col, row = _lonlat_to_indices(lon, lat, bbox, ncols, nrows)
                max_depth = max(max_depth, float(depth_m[row, col]))
            blocked = max_depth >= road_threshold_m
            if blocked:
                impact.roads_blocked += 1
            impact.roads_detail.append(
                RoadImpact(road_id=feat.get("properties", {}).get("road_id", feat.get("id")),
                           blocked=blocked, max_depth_m=max_depth)
            )

    # ---------------- Agricultura ----------------
    if snapshot.farmland_polygon and include_farmland and flood_mask.any():
        impact.farmland_flooded_ha = _farmland_flooded_ha(
            snapshot.farmland_polygon, flood_mask, bbox, cell_area_m2
        )

    return impact


def _farmland_flooded_ha(
    farmland_geojson: dict[str, Any],
    flood_mask: np.ndarray,
    bbox: tuple[float, float, float, float],
    cell_area_m2: float,
) -> float:
    """
    Hectáreas agrícolas sumergidas.

    Método: convierte cada celda inundada a su centroide geográfico y cuenta
    cuántos caen dentro del(los) polígono(s) agrícola(s). Precisión de celda,
    costo O(celdas inundadas log n) con STRtree.
    """
    # Acepta Feature individual o FeatureCollection completo
    feats = farmland_geojson.get("features") or [farmland_geojson]
    geoms = []
    for f in feats:
        try:
            g = shape(f["geometry"])
            if g.geom_type in ("Polygon", "MultiPolygon") and not g.is_empty:
                geoms.append(g)
        except (KeyError, TypeError, ValueError):
            continue
    if not geoms:
        return 0.0
    tree = STRtree(geoms)

    nrows, ncols = flood_mask.shape
    min_lon, min_lat, max_lon, max_lat = bbox
    rows, cols = np.nonzero(flood_mask)
    flooded_cells = 0
    for row, col in zip(rows, cols):
        lon = min_lon + (col + 0.5) / ncols * (max_lon - min_lon)
        lat = max_lat - (row + 0.5) / nrows * (max_lat - min_lat)
        point = Point(lon, lat)
        idxs = tree.query(point)
        # Shapely 2: query devuelve índices de geometrías candidatas (bbox)
        for i in np.atleast_1d(idxs):
            if geoms[int(i)].contains(point):
                flooded_cells += 1
                break
    return flooded_cells * cell_area_m2 / 10_000.0
