"""
gee_client.py — Inicialización de Google Earth Engine.

Centraliza la autenticación (cuenta de servicio o `earthengine authenticate`)
y expone el módulo `ee` listo para usar. Si GEE no está configurado, los
consumidores deben degradar a modo demo/local.
"""

from __future__ import annotations

import json
import logging

from hidroalert.config import CONFIG

logger = logging.getLogger(__name__)

# Estado del singleton
_ee = None
_initialized = False


def get_ee():
    """
    Devuelve el módulo `ee` inicializado (singleton perezoso).

    Estrategia de autenticación:
        1. Si HIDROALERT_GEE_SERVICE_ACCOUNT_JSON apunta a un JSON válido,
           se usa `ee.ServiceAccountCredentials`.
        2. En caso contrario, se usan las credenciales interactivas generadas
           por `earthengine authenticate`.

    Raises:
        RuntimeError: si las credenciales no están configuradas o falla la
            conexión con el servicio de Earth Engine.
    """
    global _ee, _initialized
    if _initialized:
        return _ee

    if not CONFIG.gee.is_configured:
        raise RuntimeError(
            "Google Earth Engine no está configurado: define "
            "HIDROALERT_GEE_PROJECT_ID en el archivo .env."
        )

    try:
        import ee  # importación perezosa: solo si GEE está configurado
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "El paquete `earthengine-api` no está instalado. "
            "Ejecuta: pip install -r requirements.txt"
        ) from exc

    try:
        sa_path = CONFIG.gee.service_account_json
        if sa_path:
            # Autenticación por cuenta de servicio
            with open(sa_path, "r", encoding="utf-8") as fh:
                key_data = json.load(fh)
            creds = ee.ServiceAccountCredentials(
                key_data.get("client_email", ""), sa_path
            )
            ee.Initialize(options={"credentials": creds, "project": CONFIG.gee.project_id})
            logger.info("GEE inicializado con cuenta de servicio %s", key_data.get("client_email"))
        else:
            # Autenticación interactiva (`earthengine authenticate`)
            ee.Initialize(project=CONFIG.gee.project_id)
            logger.info("GEE inicializado con credenciales de usuario (proyecto %s)", CONFIG.gee.project_id)
        _ee = ee
        _initialized = True
        return _ee
    except Exception as exc:
        _initialized = False
        raise RuntimeError(f"No se pudo inicializar Google Earth Engine: {exc}") from exc


def is_available() -> bool:
    """True si GEE puede inicializarse sin lanzar excepción."""
    try:
        get_ee()
        return True
    except RuntimeError:
        return False
