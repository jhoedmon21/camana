"""Módulo 2 — Motor de simulación hidrológica (profundidad, volumen e impacto)."""

from hidroalert.hydrology.simulation_engine import simulate_flood
from hidroalert.hydrology.impact import compute_impact_matrix

__all__ = ["simulate_flood", "compute_impact_matrix"]
