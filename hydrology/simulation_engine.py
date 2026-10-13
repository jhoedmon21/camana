"""
simulation_engine.py — Motor de simulación hidrológica (Módulo 2).

Modelo conceptual (ráster, celda = aoi.scale_m²):
    * El campo HAND (m sobre el drenaje más cercano) define el "relleno"
      del valle: una celda se inunda cuando la lámina supera su HAND.
    * La precipitación (mm/h) y el incremento de caudal (%) elevan el
      "nivel de energía del agua" → lámina máxima en el cauce (HAND=0).
    * La lámina por celda = max(0, lámina_cauce − HAND_celda).
    * Volumen = Σ (lámina_celda × área_celda)   [m³]
              = Área inundada × Profundidad media HAND  (identidad del
                entregable, válida porque la profundidad media es
                Volumen/Área por definición).

Parámetros interactivos (sliders del dashboard):
    precipitation_mm_h : 0 – 200 mm/h
    flow_increase_pct  : 0 – 300 %  (incremento de caudal en río/quebrada)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import numpy as np

from hidroalert.models import AreaSnapshot, SimulationResult, ImpactMatrix
from hidroalert.hydrology.impact import compute_impact_matrix
from hidroalert.hydrology.concentration import overland_concentration
from hidroalert.data_ingest.aoi import AreaOfInterest
from hidroalert.config import BANKFULL_DEPTH_M

logger = logging.getLogger(__name__)

# --- Parámetros de calibración del modelo conceptual ---
# Calibrados (2026-10) para ser consistentes con los bankfull por río:
# con FEN extremo (120 mm/h · +250 %) la lámina en cauce debe superar el
# bankfull del río más profundo calibrado (Tumbes 3.0 m) — ROJO —; con el
# escenario Moderado (35 mm/h · +80 %) debe quedar bajo el más bajo (1.0 m).
# Lámina máxima en el cauce (m) producida por lluvia sola
RAINFALL_DEPTH_COEF = 0.35
# Lámina adicional (m) producida por el incremento de caudal
FLOW_DEPTH_COEF = 1.95
# Factor de concentración de la cuenca: la escorrentía de toda la cuenca
# converge al cauce, por lo que la lámina en el cauce supera la lluvia puntual
BASIN_CONCENTRATION = 25.0
# Curva de concentración (dimensionless) para el runoff de lluvia
RUNOFF_CURVE_NUMBER_FACTOR = 0.118
# Umbral de profundidad para considerar bloqueada una vía (m)
ROAD_BLOCK_DEPTH_M = 0.20
# Capacidad de banco del cauce (bankfull, m): la lámina por debajo de este
# nivel queda contenida en el canal y NO se considera desborde. Solo el agua
# que excede la capacidad del cauce inunda la llanura de inundación.
# (Valor por defecto; configurable por quebrada vía HIDROALERT_BANKFULL_DEPTH_M)
DEFAULT_BANKFULL_DEPTH_M = 1.0
# Umbral de profundidad para considerar afectado un edificio (m)
BUILDING_AFFECTED_DEPTH_M = 0.15


def _channel_depth_m(precipitation_mm_h: float, flow_increase_pct: float) -> float:
    """
    Lámina total en el cauce (HAND=0) para el escenario dado.

    Combina:
        * escorrentía de la lluvia: mm/h × factor de concentración → m;
        * aporte de caudal: raíz del porcentaje (relación física
          aproximada Q ∝ h^(5/3) de Manning → h ∝ Q^0.6, aquí linealizada
          con raíz para suavizar el slider).
    """
    rain_depth_m = (
        (precipitation_mm_h / 1000.0)
        * RUNOFF_CURVE_NUMBER_FACTOR
        * BASIN_CONCENTRATION
        * RAINFALL_DEPTH_COEF
    )
    flow_depth_m = FLOW_DEPTH_COEF * np.sqrt(flow_increase_pct / 100.0)
    return float(rain_depth_m + flow_depth_m)


def simulate_flood(
    snapshot: AreaSnapshot,
    precipitation_mm_h: float = 20.0,
    flow_increase_pct: float = 50.0,
    scenario_label: str = "",
    fast_mode: bool = False,
    bankfull_depth_m: float | None = None,
    include_overland: bool = False,
) -> SimulationResult:
    """
    Ejecuta la simulación hidrológica interactiva (Módulo 2).

    Args:
        snapshot:          contexto del área (Módulo 1).
        precipitation_mm_h: precipitación acumulada 0–200 mm/h.
        flow_increase_pct:  incremento de caudal 0–300 %.
        scenario_label:     etiqueta del escenario (ej. "Torrencial / FEN Extremo").
        fast_mode:          True omite vías y agricultura (para series de 48 h;
                            mantiene edificios, profundidad y volumen).
        bankfull_depth_m:   capacidad de banco del cauce (m). None usa el global
                            (BANKFULL_DEPTH_M); la API pasa el valor calibrado
                            por río (config.bankfull_for_zone).
        include_overland:   True añade la CONCENTRACIÓN DE AGUA SOBRE TERRENO
                            (escorrentía superficial ruteada con D8: pozas en
                            depresiones, ver hydrology/concentration.py) a la
                            lámina de desborde del cauce.

    Returns:
        SimulationResult con lámina por celda, volumen y matriz de impacto.
    """
    if snapshot.hand.size == 0:
        raise ValueError("El snapshot no contiene matriz HAND; ejecute primero la ingesta.")

    hand = np.nan_to_num(snapshot.hand, nan=60.0)  # NaN = ladera lejana: nunca inunda
    channel_depth = _channel_depth_m(precipitation_mm_h, flow_increase_pct)

    # Lámina de DESBORDE por celda: solo el agua que supera la capacidad de
    # banco del cauce (bankfull) sale del canal y sube por la llanura según
    # el HAND local. Los eventos menores quedan contenidos en el cauce.
    # Bankfull por río (calibración) con fallback al global/env.
    bankfull = (
        bankfull_depth_m
        if bankfull_depth_m is not None and bankfull_depth_m > 0
        else (BANKFULL_DEPTH_M if BANKFULL_DEPTH_M > 0 else DEFAULT_BANKFULL_DEPTH_M)
    )
    overbank = max(0.0, channel_depth - bankfull)
    depth_m = np.clip(overbank - hand, 0.0, None)

    # --- Concentración de agua sobre terreno (escorrentía superficial D8)
    # Pozas en depresiones de ladera, además del desborde del cauce. La red
    # de drenaje (HAND≈0) absorbe la escorrentía que la alcanza, así que no
    # hay doble conteo con el componente de cauce.
    overland_depth = None
    overland_stats = {"volume_m3": 0.0, "area_m2": 0.0, "max_depth_m": 0.0}
    if include_overland and precipitation_mm_h > 0:
        overland_depth, overland_stats = overland_concentration(
            snapshot, precipitation_mm_h=precipitation_mm_h
        )
        # Lámina total sobre terreno = desborde del cauce + pozas de ladera
        depth_m = depth_m + overland_depth

    flood_mask = depth_m > 0.01  # celdas con más de 1 cm de lámina

    # --- Volumen total (m³): Σ lámina × área de celda
    water_volume_m3 = float(depth_m[flood_mask].sum() * snapshot.cell_area_m2)

    # --- Impacto sobre infraestructura (fast_mode omite capas costosas)
    impact = compute_impact_matrix(
        snapshot=snapshot,
        depth_m=depth_m,
        flood_mask=flood_mask,
        bbox=snapshot.bbox,
        cell_area_m2=snapshot.cell_area_m2,
        building_threshold_m=BUILDING_AFFECTED_DEPTH_M,
        road_threshold_m=ROAD_BLOCK_DEPTH_M,
        include_roads=not fast_mode,
        include_farmland=not fast_mode,
    )

    return SimulationResult(
        aoi_name=snapshot.aoi_name,
        bbox=snapshot.bbox,
        precipitation_mm_h=precipitation_mm_h,
        flow_increase_pct=flow_increase_pct,
        depth_m=depth_m,
        flood_mask=flood_mask,
        water_volume_m3=water_volume_m3,
        water_volume_lits=water_volume_m3 * 1000.0,
        flooded_area_m2=float(flood_mask.sum() * snapshot.cell_area_m2),
        impact=impact,
        observed_water_area_m2=snapshot.observed_water_area_m2,
        overland_depth_m=overland_depth,
        overland_volume_m3=overland_stats["volume_m3"],
        overland_area_m2=overland_stats["area_m2"],
        overland_max_depth_m=overland_stats["max_depth_m"],
        scenario_label=scenario_label or f"{precipitation_mm_h:.0f} mm/h · +{flow_increase_pct:.0f} % caudal",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def scenario_presets() -> dict[str, dict[str, float]]:
    """
    Escenarios predefinidos del dashboard (Módulo 3).

    Returns:
        dict con nombre de escenario → parámetros (mm/h, % caudal).
    """
    return {
        "Lluvia Ligera": {"precipitation_mm_h": 5.0, "flow_increase_pct": 10.0},
        "Moderada": {"precipitation_mm_h": 35.0, "flow_increase_pct": 80.0},
        "Torrencial / FEN Extremo": {"precipitation_mm_h": 120.0, "flow_increase_pct": 250.0},
    }
