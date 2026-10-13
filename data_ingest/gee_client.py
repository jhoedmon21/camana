"""
gee_client.py — Inicialización de Google Earth Engine.

Centraliza la autenticación (cuenta de servicio o `earthengine authenticate`)
y expone el módulo `ee` listo para usar. Si GEE no está configurado, los
consumidores deben degradar a modo demo/local.
"""

from __future__ import annotations

import json
import logging
import os

from hidroalert.config import CONFIG

logger = logging.getLogger(__name__)

# Estado del singleton
_ee = None
_initialized = False


def _materialize_oauth_token_file() -> bool:
    """
    Serverless (Vercel/Railway): materializa el token OAuth interactivo
    desde la variable de entorno HIDROALERT_GEE_CREDENTIALS_JSON (el
    contenido de ~/.config/earthengine/credentials) en la ruta que la
    librería `ee` espera. `os.path.expanduser` respeta $HOME, así que si
    el HOME del proceso no es escribible se redirige a /tmp.

    Returns:
        True si el token se escribió; False si la variable no está definida.
    """
    import json as _json

    raw = (os.environ.get("HIDROALERT_GEE_CREDENTIALS_JSON") or "").strip()
    if not raw:
        return False
    try:
        _json.loads(raw)  # valida que sea JSON bien formado
    except ValueError as exc:
        raise RuntimeError(
            "HIDROALERT_GEE_CREDENTIALS_JSON no es JSON válido: "
            "debe contener el archivo ~/.config/earthengine/credentials."
        ) from exc
    for home in (os.environ.get("HOME") or "/tmp", "/tmp"):
        cred_dir = os.path.join(home, ".config", "earthengine")
        try:
            os.makedirs(cred_dir, exist_ok=True)
            with open(os.path.join(cred_dir, "credentials"), "w", encoding="utf-8") as fh:
                fh.write(raw)
            os.environ["HOME"] = home  # expanduser('~') usará este HOME
            logger.info("Token OAuth GEE materializado en %s", cred_dir)
            return True
        except OSError:
            continue
    raise RuntimeError("No se pudo escribir el token OAuth de GEE (HOME y /tmp ilegibles).")


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
            # Autenticación interactiva (`earthengine authenticate`), incluido
            # el despliegue serverless donde el token viaja por env var.
            _materialize_oauth_token_file()
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
