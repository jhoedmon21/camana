"""
forecast.py — Pronóstico horario de precipitación para el AOI.

Convierte a HidroAlert de un sistema *reactivo* (simular lluvia manual) a
uno *predictivo*: pronóstico horario → simulación → línea de tiempo de
niveles de alerta (predecir CUÁNDO el nivel sube, no solo si sube).

Fuentes (en orden de preferencia si hay credenciales):
    1. Google Maps Platform Weather API (WeatherNext 3) — requiere
       HIDROALERT_GOOGLE_WEATHER_API_KEY. Precipitación horaria del modelo
       insignia de Google DeepMind (5–11 km, actualización 1 h).
    2. Open-Meteo (open-meteo.com) — gratuito, sin key, agrega ICON/GFS/ECMWF.

Ambas devuelven el mismo contrato: lista de (hora, mm/h) + pico.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import requests

from hidroalert.config import CONFIG
from hidroalert.data_ingest.aoi import AreaOfInterest

logger = logging.getLogger(__name__)

# --- Open-Meteo ---
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
# --- Google Maps Platform Weather API (WeatherNext 3) ---
GOOGLE_WEATHER_HOURLY_URL = "https://weather.googleapis.com/v1/forecast/hours:lookup"

REQUEST_TIMEOUT_S = 25


def forecast_precipitation_open_meteo(aoi: AreaOfInterest, hours: int = 48) -> dict[str, Any]:
    """
    Pronóstico horario de precipitación vía Open-Meteo (sin API key).

    Args:
        aoi:   área de interés (usa su centroide).
        hours: horas de pronóstico a consultar (máx. razonable: 96).

    Returns:
        dict: {'series': [(hora_iso, mm_h), ...], 'peak_mm_h': float,
               'peak_time': str, 'source': 'open-meteo'}
    """
    center_lat = (aoi.min_lat + aoi.max_lat) / 2
    center_lon = (aoi.min_lon + aoi.max_lon) / 2
    params = {
        "latitude": round(center_lat, 4),
        "longitude": round(center_lon, 4),
        "hourly": "precipitation",
        "forecast_hours": min(hours, 96),
        "timezone": "UTC",
    }
    resp = requests.get(OPEN_METEO_URL, params=params, timeout=REQUEST_TIMEOUT_S)
    resp.raise_for_status()
    data = resp.json()
    times: list[str] = data.get("hourly", {}).get("time", [])
    mmhs: list[float] = [
        float(v) if v is not None else 0.0
        for v in data.get("hourly", {}).get("precipitation", [])
    ]
    if not times or not mmhs:
        raise RuntimeError("Respuesta de Open-Meteo sin serie de precipitación.")

    series = list(zip(times[:hours], mmhs[:hours]))
    peak_time, peak_val = max(series, key=lambda t: t[1])
    return {
        "series": series,
        "peak_mm_h": float(peak_val),
        "peak_time": peak_time,
        "source": "open-meteo",
    }


def forecast_precipitation_weathernext(aoi: AreaOfInterest, hours: int = 48) -> dict[str, Any]:
    """
    Pronóstico horario vía WeatherNext 3 (Google Maps Platform Weather API).

    Requiere HIDROALERT_GOOGLE_WEATHER_API_KEY; lanza RuntimeError si no está
    configurada o la respuesta no es válida (degradación manual a Open-Meteo).

    Nota: la API de Weather expone el acumulado de precipitación (qpf, mm)
    por hora; se interpreta como mm/h para el motor hidrológico.
    """
    if not CONFIG.gmaps.is_configured:
        raise RuntimeError(
            "WeatherNext requiere HIDROALERT_GOOGLE_WEATHER_API_KEY en .env; "
            "usando Open-Meteo como alternativa gratuita."
        )
    center_lat = (aoi.min_lat + aoi.max_lat) / 2
    center_lon = (aoi.min_lon + aoi.max_lon) / 2
    params = {
        "key": CONFIG.gmaps.api_key,
        "location.latitude": round(center_lat, 4),
        "location.longitude": round(center_lon, 4),
        "hours": min(hours, 240),
        "unitsSystem": "METRIC",
    }
    resp = requests.get(GOOGLE_WEATHER_HOURLY_URL, params=params, timeout=REQUEST_TIMEOUT_S)
    resp.raise_for_status()
    data = resp.json()

    series: list[tuple[str, float]] = []
    for h in data.get("forecastHours", []):
        t = h.get("interval", {}).get("startTime", "")
        # qpf (Quantity of Precipitation Forecast) en mm por hora
        mm = (
            h.get("precipitation", {}).get("qpf", {}).get("millimeters")
        )
        if t and mm is not None:
            series.append((t, float(mm)))
    if not series:
        raise RuntimeError("Respuesta de WeatherNext sin precipitación horaria utilizable.")

    peak_time, peak_val = max(series, key=lambda t: t[1])
    return {
        "series": series,
        "peak_mm_h": float(peak_val),
        "peak_time": peak_time,
        "source": "weathernext-3",
    }


def forecast_precipitation(aoi: AreaOfInterest, hours: int = 48) -> dict[str, Any]:
    """
    Pronóstico con mejor fuente disponible: WeatherNext 3 si hay API key,
    Open-Meteo como fallback gratuito (siempre operativo).
    """
    try:
        return forecast_precipitation_weathernext(aoi, hours)
    except (RuntimeError, requests.RequestException) as exc:
        logger.info("WeatherNext no disponible (%s); usando Open-Meteo.", str(exc)[:120])
        return forecast_precipitation_open_meteo(aoi, hours)
