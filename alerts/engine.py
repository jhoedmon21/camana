"""
engine.py — Motor de alertas condicionales (Módulo 4).

Convierte un `SimulationResult` en una decisión de alerta:
    VERDE    — situación normal; sin amenaza.
    AMARILLO — precaución: hidrología favorable a inundación incipiente.
    ROJO     — evacuación inminente por desborde / falla de quebrada.

La decisión considera simultáneamente: edificios afectados, profundidad
máxima, volumen desbordado y área inundada, contra los umbrales de
`config.AlertThresholds` (configurables por .env).
"""

from __future__ import annotations

import logging

from hidroalert.config import CONFIG
from hidroalert.models import SimulationResult, AlertDecision

logger = logging.getLogger(__name__)

# Jerarquía de severidad (mayor índice = más severo)
_LEVEL_RANK = {"VERDE": 0, "AMARILLO": 1, "ROJO": 2}


def evaluate_alert(result: SimulationResult) -> AlertDecision:
    """
    Evalúa la simulación contra los umbrales y emite la decisión de alerta.

    Regla: el nivel final es el más severo disparado por cualquier criterio.
    Cada criterio acumula razones legibles para el informe y las notificaciones.
    """
    t = CONFIG.thresholds
    level = "VERDE"
    reasons: list[str] = []

    def _escalate(candidate: str, reason: str) -> None:
        nonlocal level
        if _LEVEL_RANK[candidate] > _LEVEL_RANK[level]:
            level = candidate
        reasons.append(f"[{candidate}] {reason}")

    hid = result.to_dict()["hydrology"]

    # --- Criterio 1: edificios/viviendas afectadas
    if result.impact.buildings_affected >= t.buildings_red:
        _escalate(
            "ROJO",
            f"{result.impact.buildings_affected} viviendas afectadas "
            f"(umbral {t.buildings_red}).",
        )
    elif result.impact.buildings_affected >= t.buildings_yellow:
        _escalate(
            "AMARILLO",
            f"{result.impact.buildings_affected} viviendas afectadas "
            f"(umbral {t.buildings_yellow}).",
        )

    # --- Criterio 2: profundidad máxima simulada
    max_depth = float(hid["max_depth_m"])
    if max_depth >= t.depth_red_m:
        _escalate(
            "ROJO",
            f"Lámina máxima de {max_depth:.2f} m: peligro para personas "
            f"(umbral {t.depth_red_m:.2f} m).",
        )
    elif max_depth >= t.depth_yellow_m:
        _escalate(
            "AMARILLO",
            f"Lámina máxima de {max_depth:.2f} m sobre el cauce "
            f"(umbral {t.depth_yellow_m:.2f} m).",
        )

    # --- Criterio 3: volumen desbordado
    vol = float(hid["water_volume_m3"])
    if vol >= t.volume_red_m3:
        _escalate("ROJO", f"Volumen desbordado {vol:,.0f} m³ (umbral {t.volume_red_m3:,.0f} m³).")
    elif vol >= t.volume_yellow_m3:
        _escalate(
            "AMARILLO",
            f"Volumen desbordado {vol:,.0f} m³ (umbral {t.volume_yellow_m3:,.0f} m³).",
        )

    # --- Criterio 4: vías bloqueadas (señal de aislamiento)
    if result.impact.roads_blocked > 0:
        _escalate(
            "AMARILLO",
            f"{result.impact.roads_blocked} vía(s) bloqueada(s): riesgo de aislamiento.",
        )

    # --- Criterio 5: caudal extremo (falla de quebrada) aunque aún no inunde
    if result.flow_increase_pct >= 200 and result.precipitation_mm_h >= 80:
        _escalate(
            "ROJO",
            "Escenario torrencial (≥200 % caudal y ≥80 mm/h): posible falla "
            "de quebrada / flujo de detritos.",
        )

    if not reasons:
        reasons.append("Parámetros dentro de rangos normales; sin amenaza detectada.")

    decision = AlertDecision(level=level, reasons=reasons, thresholds_used=t.to_dict())
    logger.info("Alerta %s para %s", level, result.aoi_name)
    return decision
