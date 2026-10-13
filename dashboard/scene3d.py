"""
scene3d.py — Vistas 3D del Centro de Observación de Emergencias (COE).

Genera escenas interactivas con PyDeck (deck.gl sobre MapLibre):

    1. `city_scene()`   — Ciudad 3D: huellas de edificios extruidas según su
       altura estimada, coloreadas por estado (afectada/no afectada) sobre
       imagen satelital, con el agua de inundación como capa de suelo.

    2. `water_surface_scene()` — Superficie 3D del terreno (DEM) con la
       lámina de agua simulada elevada sobre el nivel del suelo; permite
       "ver" el valle y el volumen de agua desde cualquier ángulo.

Los datos provienen del Módulo 1 (GEE real) y del Módulo 2 (simulación).
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pydeck as pdk

from hidroalert.models import AreaSnapshot, SimulationResult

logger = logging.getLogger(__name__)

# Paleta COE
COLOR_SAFE = [90, 130, 165, 220]        # edificio fuera de riesgo (azul grisáceo)
COLOR_AFFECTED = [211, 47, 47, 240]     # vivienda afectada (rojo)
COLOR_WATER_DEEP = [13, 71, 161, 200]   # lámina severa
COLOR_WATER_MID = [30, 136, 229, 170]   # lámina moderada
COLOR_WATER_SHALLOW = [129, 212, 250, 140]  # lámina poco profunda

# Altura estimada por piso (m) — MS Buildings no trae altura en todas las geometrías
FLOOR_HEIGHT_M = 3.0


def _bbox_center(bbox) -> tuple[float, float]:
    min_lon, min_lat, max_lon, max_lat = bbox
    return (min_lon + max_lon) / 2, (min_lat + max_lat) / 2


def _building_height(props: dict[str, Any]) -> float:
    """
    Altura del edificio (m). Usa 'height' si existe (MS Buildings), o
    estima por número de pisos (1–3) si viene 'num_floors'; por defecto 6 m.
    """
    h = props.get("height") or props.get("Height")
    if h:
        try:
            return max(3.0, float(h))
        except (TypeError, ValueError):
            pass
    floors = props.get("num_floors") or props.get("NumFloors")
    if floors:
        try:
            return max(3.0, float(floors) * FLOOR_HEIGHT_M)
        except (TypeError, ValueError):
            pass
    return 6.0


def _flood_lookup(result: SimulationResult) -> dict[tuple[int, int], float]:
    """Índice (col,row) → profundidad para intersección rápida edificios/agua."""
    from hidroalert.hydrology.impact import _lonlat_to_indices

    depth_map: dict[tuple[int, int], float] = {}
    rows, cols = np.nonzero(result.flood_mask)
    for r, c in zip(rows, cols):
        depth_map[(int(c), int(r))] = float(result.depth_m[r, c])
    return depth_map


def city_scene(
    snapshot: AreaSnapshot,
    result: SimulationResult,
    height: int = 560,
) -> pdk.Deck:
    """
    Ciudad 3D del COE: edificios extruidos + lámina de inundación en el suelo.

    Args:
        snapshot: contexto geográfico (edificios GEE).
        result:   simulación actual (lámina, máscara).
        height:   altura del lienzo en px.

    Returns:
        Objeto pdk.Deck listo para `st.pydeck_chart`.
    """
    lon0, lat0 = _bbox_center(result.bbox)
    zoom0 = 13.5

    # ---------- Edificios ----------
    bld_feats: list[dict[str, Any]] = []
    if snapshot.buildings:
        depth_map = _flood_lookup(result)
        ncols = result.flood_mask.shape[1]
        nrows = result.flood_mask.shape[0]
        for feat in snapshot.buildings["features"]:
            try:
                coords = feat["geometry"]["coordinates"][0]
            except (KeyError, IndexError, TypeError):
                continue
            # Polígono → lista de posiciones [lon, lat]
            positions = [[c[0], c[1]] for c in coords if len(c) >= 2]
            if len(positions) < 3:
                continue
            clon = sum(p[0] for p in positions) / len(positions)
            clat = sum(p[1] for p in positions) / len(positions)
            from hidroalert.hydrology.impact import _lonlat_to_indices
            col, row = _lonlat_to_indices(clon, clat, result.bbox, ncols, nrows)
            d = depth_map.get((col, row), 0.0)
            affected = d >= 0.15
            bld_feats.append({
                "polygon": positions,
                "height": _building_height(feat.get("properties", {})),
                "color": COLOR_AFFECTED if affected else COLOR_SAFE,
                "affected": affected,
                "depth_cm": round(d * 100),
            })

    bld_layer = pdk.Layer(
        "PolygonLayer",
        data=bld_feats,
        get_polygon="polygon",
        get_elevation="height",
        get_fill_color="color",
        get_line_color=[255, 255, 255, 40],
        extruded=True,
        wireframe=False,
        pickable=True,
        auto_highlight=True,
    )

    # ---------- Agua (celdas inundadas como placas en el suelo) ----------
    from hidroalert.hydrology.impact import _lonlat_to_indices  # noqa: F401 (ya arriba)
    min_lon, min_lat, max_lon, max_lat = result.bbox
    nrows, ncols = result.flood_mask.shape
    dlon = (max_lon - min_lon) / ncols
    dlat = (max_lat - min_lat) / nrows
    rows, cols = np.nonzero(result.flood_mask)
    step = max(1, len(rows) // 9000)  # límite de rendimiento
    water_feats: list[dict[str, Any]] = []
    for r, c in zip(rows[::step], cols[::step]):
        d = float(result.depth_m[r, c])
        color = (
            COLOR_WATER_DEEP if d > 0.8
            else COLOR_WATER_MID if d > 0.3
            else COLOR_WATER_SHALLOW
        )
        lon = min_lon + (c + 0.5) * dlon
        lat = max_lat - (r + 0.5) * dlat
        water_feats.append({
            "position": [lon, lat],
            "color": color,
            "radius": max(dlon, dlat) * 111_320 * 0.75,  # ~3/4 de celda
            "depth_cm": round(d * 100),
        })

    water_layer = pdk.Layer(
        "ScatterplotLayer",
        data=water_feats,
        get_position="position",
        get_radius="radius",
        get_fill_color="color",
        radius_min_pixels=2,
        radius_max_pixels=18,
        pickable=True,
        stroked=False,
    )

    view = pdk.ViewState(
        latitude=lat0, longitude=lon0, zoom=zoom0, pitch=55, bearing=-18,
    )
    deck = pdk.Deck(
        layers=[water_layer, bld_layer],
        initial_view_state=view,
        map_style=pdk.map_styles.SATELLITE,
        tooltip={
            "html": "<b>Edificio</b><br/>Altura: {height} m<br/>"
                    "Estado: {affected}<br/>Lámina: {depth_cm} cm",
            "style": {"backgroundColor": "#0d1b2a", "color": "#e0e6ed",
                      "fontSize": "12px"},
        },
        height=height,
    )
    return deck


def water_surface_scene(
    snapshot: AreaSnapshot,
    result: SimulationResult,
    height: int = 560,
    exaggeration: float = 12.0,
) -> pdk.Deck:
    """
    Superficie 3D del valle: terreno (elevación) + lámina de agua flotante.

    Se construye con `TerrainLayer`-like mediante `SimpleMeshLayer`? No: se
    usa la representación más robusta en PyDeck — una malla de columnas
    (`ColumnLayer`) donde cada celda inundada es una columna cuya altura es
    la profundidad (exagerada) y el terreno queda de referencia satelital.

    Args:
        exaggeration: multiplicador de la lámina para que sea visible (×12).
    """
    lon0, lat0 = _bbox_center(result.bbox)
    min_lon, min_lat, max_lon, max_lat = result.bbox
    nrows, ncols = result.flood_mask.shape
    dlon = (max_lon - min_lon) / ncols
    dlat = (max_lat - min_lat) / nrows

    rows, cols = np.nonzero(result.flood_mask)
    step = max(1, len(rows) // 7000)
    cols_data: list[dict[str, Any]] = []
    for r, c in zip(rows[::step], cols[::step]):
        d = float(result.depth_m[r, c])
        color = (
            COLOR_WATER_DEEP if d > 0.8
            else COLOR_WATER_MID if d > 0.3
            else COLOR_WATER_SHALLOW
        )
        lon = min_lon + (c + 0.5) * dlon
        lat = max_lat - (r + 0.5) * dlat
        cols_data.append({
            "position": [lon, lat],
            "elevation": max(2.0, d * exaggeration),  # m (exagerado)
            "color": color,
            "depth_cm": round(d * 100),
        })

    water_cols = pdk.Layer(
        "ColumnLayer",
        data=cols_data,
        get_position="position",
        get_elevation="elevation",
        get_fill_color="color",
        radius=max(dlon, dlat) * 111_320 * 0.7,
        extruded=True,
        pickable=True,
        coverage=0.9,
    )

    view = pdk.ViewState(
        latitude=lat0, longitude=lon0, zoom=13, pitch=62, bearing=-30,
    )
    return pdk.Deck(
        layers=[water_cols],
        initial_view_state=view,
        map_style=pdk.map_styles.SATELLITE,
        tooltip={
            "html": "<b>Lámina de agua</b><br/>{depth_cm} cm",
            "style": {"backgroundColor": "#0d1b2a", "color": "#e0e6ed",
                      "fontSize": "12px"},
        },
        height=height,
    )
