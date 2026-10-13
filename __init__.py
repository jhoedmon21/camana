"""
HidroAlert — Monitoreo, simulación y alerta temprana de inundaciones,
desbordes de ríos y fallas de quebradas.

Workspace: jhons-workspace-amus9
Módulos:
    1. data_ingest  — Ingesta satelital (GEE Sentinel-1 SAR, HAND, edificios, mapas Google).
    2. hydrology    — Motor de simulación hidrológica (profundidad HAND, volumen e impacto).
    3. dashboard    — Dashboard interactivo Streamlit (escenarios, mapas e indicadores).
    4. alerts       — Motor de alertas (VERDE/AMARILLO/ROJO), Twilio, webhooks y reportes.
"""

__version__ = "1.0.0"
__app_name__ = "HidroAlert"
