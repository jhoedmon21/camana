"""
index.py — Punto de entrada ASGI para Vercel (función serverless).

Vercel ejecuta este archivo como función Python y expone la `app` FastAPI.
El repo raíz ES el paquete `hidroalert` (tiene __init__.py), pero en el
entorno de despliegue la carpeta puede no llamarse así: se registra como
paquete `hidroalert` sea cual sea su nombre de directorio.

Localmente nada cambia: sigue usándose
    uvicorn hidroalert.api.main:app --port 8000
desde el directorio padre.
"""

from __future__ import annotations

import importlib.util
import os
import sys

# Informes a /tmp: en serverless el FS del proyecto es de solo lectura
os.environ.setdefault("HIDROALERT_REPORTS_DIR", "/tmp/hidroalert-reports")

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PARENT = os.path.dirname(_ROOT)
if _PARENT not in sys.path:
    sys.path.insert(0, _PARENT)

try:
    import hidroalert  # local: el directorio ya se llama 'hidroalert'
except ImportError:  # despliegue: registrar el root con ese nombre
    _spec = importlib.util.spec_from_file_location(
        "hidroalert",
        os.path.join(_ROOT, "__init__.py"),
        submodule_search_locations=[_ROOT],
    )
    _pkg = importlib.util.module_from_spec(_spec)
    sys.modules["hidroalert"] = _pkg
    _spec.loader.exec_module(_pkg)

from hidroalert.api.main import app  # noqa: E402,F401
