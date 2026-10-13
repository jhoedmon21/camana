"""
timeline.py — Línea de tiempo de alertas a partir del pronóstico horario.

El cambio de paradigma estilo WeatherNext 3: en lugar de simular un valor
manual de lluvia, se propaga **cada hora del pronóstico** por el motor
hidrológico y se construye la evolución del nivel de alerta:

    pronóstico horario → simulate_flood(hora) → evaluate_alert(hora)
    ⇒ ¿CUÁNDO sube a AMARILLO/ROJO? (anticipación, no solo detección)

Salida serializable para dashboard/API:
    * timeline: [{hora, mm_h, nivel, volumen_m3, viviendas, ...}, ...]
    * peak:     hora e intensidad del pico de lluvia.
    * rise_to:  primer cruce a AMARILLO y a ROJO (None si no ocurre).
"""

from __future__ import annotations

import logging
from typing import Any

from hidroalert.data_ingest.aoi import AreaOfInterest
from hidroalert.hydrology.simulation_engine import simulate_flood
from hidroalert.alerts.engine import evaluate_alert
from hidroalert.models import AreaSnapshot

logger = logging.getLogger(__name__)

_NIVELES = {"VERDE": 0, "AMARILLO": 1, "ROJO": 2}


def build_alert_timeline(
    snapshot: AreaSnapshot,
    forecast: dict[str, Any],
    max_hours: int = 48,
    bankfull_depth_m: float | None = None,
    include_overland: bool = True,
) -> dict[str, Any]:
    """
    Propaga el pronóstico horario por el motor hidrológico y de alertas.

    Args:
        snapshot:  contexto del área (Módulo 1); se reutiliza la geometría.
        forecast:  salida de `forecast_precipitation()` (series de mm/h).
        max_hours: límite de horas a propagar (costo O(h) simulaciones).
        bankfull_depth_m: capacidad de banco del cauce (calibrada por río).
        include_overland: incorpora la CONCENTRACIÓN DE AGUA SOBRE TERRENO
            (escorrentía superficial D8) a cada hora del pronóstico —
            True por defecto: la predicción de lluvias debe anticipar no
            solo el desborde del cauce, sino dónde se concentra el agua
            sobre el terreno.

    Returns:
        dict con 'timeline', 'peak' y 'rise_to' (primer cruce por nivel).
    """
    series = forecast.get("series", [])[:max_hours]
    flow_increase_pct = float(forecast.get("flow_increase_pct", 0.0))

    timeline: list[dict[str, Any]] = []
    first_cross: dict[str, str] = {}

    for hour_iso, mm_h in series:
        result = simulate_flood(
            snapshot,
            precipitation_mm_h=float(mm_h),
            flow_increase_pct=flow_increase_pct,
            scenario_label=f"Pronóstico {hour_iso}",
            fast_mode=True,  # series largas: omite vías/cultivos por hora
            bankfull_depth_m=bankfull_depth_m,
            include_overland=include_overland,
        )
        decision = evaluate_alert(result)
        hid = result.to_dict()["hydrology"]
        timeline.append(
            {
                "time": hour_iso,
                "mm_h": round(float(mm_h), 2),
                "level": decision.level,
                "volume_m3": hid["water_volume_m3"],
                "overland_volume_m3": hid["overland_volume_m3"],
                "flooded_ha": hid["flooded_area_ha"],
                "buildings": result.impact.buildings_affected,
                "roads_blocked": result.impact.roads_blocked,
                "reasons": decision.reasons[:2],  # top-2 para payload ligero
            }
        )
        for nivel in ("AMARILLO", "ROJO"):
            if (
                _NIVELES[decision.level] >= _NIVELES[nivel]
                and nivel not in first_cross
            ):
                first_cross[nivel] = hour_iso

    return {
        "timeline": timeline,
        "peak": {
            "mm_h": forecast.get("peak_mm_h", 0.0),
            "time": forecast.get("peak_time", ""),
            "source": forecast.get("source", ""),
        },
        "rise_to": first_cross,
    }
