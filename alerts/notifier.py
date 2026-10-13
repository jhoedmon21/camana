"""
notifier.py — Notificaciones de emergencia (Módulo 4).

Canales soportados:
    * Twilio SMS y WhatsApp (credenciales en .env).
    * Webhook HTTP POST a un centro de operaciones (Defensa Civil / COER)
      con el payload JSON completo de la alerta.

Todas las funciones degradan silenciosamente (log de aviso) cuando las
credenciales no están configuradas, para que la simulación nunca falle por
el canal de salida.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import requests

from hidroalert.config import CONFIG
from hidroalert.models import SimulationResult, AlertDecision

logger = logging.getLogger(__name__)

# Reemplazos previos a la conversión latin-1: emojis decorativos del mensaje
# de alerta se eliminan y los semánticos se transliteran a texto plano
# (para SMS legacy e informes PDF con fuentes core).
_TRANSLIT_REPLACEMENTS = (
    ("🚨", "[ALERTA]"),
    ("⛔", ""),
    ("⚠️", "[PRECAUCION]"),
    ("⚠", "[PRECAUCION]"),
    ("✅", "[OK]"),
    ("📍", ""),
    ("🌧️", ""),
    ("🌧", ""),
    ("💧", ""),
    ("🌊", ""),
    ("🏠", ""),
    ("🚧", ""),
    ("🕒", "Hora:"),
    ("—", "-"),
    ("≥", ">="),
    ("³", "3"),
)


def _latin1_safe(text: str) -> str:
    """Convierte un texto a uno representable en latin-1 (SMS legacy / PDF)."""
    for old, new in _TRANSLIT_REPLACEMENTS:
        text = text.replace(old, new)
    return text.encode("latin-1", "replace").decode("latin-1")


def build_alert_payload(result: SimulationResult, decision: AlertDecision) -> dict[str, Any]:
    """
    Construye el payload JSON estándar de emergencia.

    Este es el contrato de integración con Defensa Civil / COER: un objeto
    con nivel, razones, hidráulica resumida, impacto y metadatos del AOI.
    """
    return {
        "sistema": "HidroAlert",
        "workspace": "jhons-workspace-amus9",
        "alerta": decision.to_dict(),
        "simulacion": result.to_dict(),
    }


def send_twilio_messages(
    message_text: str,
    recipients: tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    """
    Envía SMS/WhatsApp vía Twilio a la lista de destinatarios configurada.

    Args:
        message_text: cuerpo del mensaje (español, ≤ 1600 caracteres).
        recipients:   tupla de números (ej. '+51987654321', 'whatsapp:+51987654321').
                      None = usar los del .env.

    Returns:
        Lista de resultados por destinatario con estado del envío.
    """
    cfg = CONFIG.twilio
    if not cfg.is_configured:
        logger.warning("Twilio no configurado (HIDROALERT_TWILIO_*); mensaje solo registrado.")
        return []

    try:
        from twilio.rest import Client
    except ImportError:
        logger.error("Paquete `twilio` no instalado; no se puede notificar por SMS/WhatsApp.")
        return []

    if recipients is None:
        recipients = cfg.recipients

    results: list[dict[str, Any]] = []
    client = Client(cfg.account_sid, cfg.auth_token)
    for dest in recipients:
        # WhatsApp requiere remitente WhatsApp; SMS remitente SMS
        if dest.lower().startswith("whatsapp:"):
            from_addr = cfg.from_whatsapp
        else:
            from_addr = cfg.from_sms
        try:
            msg = client.messages.create(body=message_text, from_=from_addr, to=dest)
            results.append({"to": dest, "sid": msg.sid, "status": "queued"})
            logger.info("Mensaje Twilio encolado a %s (SID %s)", dest, msg.sid)
        except Exception as exc:
            results.append({"to": dest, "status": "error", "error": str(exc)})
            logger.error("Fallo Twilio a %s: %s", dest, exc)
    return results


def send_webhook_coer(payload: dict[str, Any]) -> bool:
    """
    Publica el payload JSON de alerta en el webhook institucional (COER).

    Returns:
        True si el webhook respondió 2xx; False en caso contrario o si no
        hay URL configurada.
    """
    cfg = CONFIG.webhook
    if not cfg.is_configured:
        logger.warning("Webhook COER no configurado (HIDROALERT_WEBHOOK_COER_URL).")
        return False
    try:
        resp = requests.post(
            cfg.coer_url,
            json=payload,
            timeout=cfg.timeout_seconds,
            headers={"Content-Type": "application/json", "X-HidroAlert-Level": payload["alerta"]["level"]},
        )
        ok = 200 <= resp.status_code < 300
        if ok:
            logger.info("Webhook COER notificado (%s)", resp.status_code)
        else:
            logger.error("Webhook COER respondió %s: %s", resp.status_code, resp.text[:200])
        return ok
    except requests.RequestException as exc:
        logger.error("Fallo del webhook COER: %s", exc)
        return False


def compose_alert_message(result: SimulationResult, decision: AlertDecision) -> str:
    """
    Redacta el mensaje humano (SMS/WhatsApp) a partir de la simulación.

    Retorna texto con emojis (ideal para WhatsApp); para canales SMS o PDF
    use `_latin1_safe()` cuando el destino no soporte Unicode.
    """
    hid = result.to_dict()["hydrology"]
    lines = [
        f"🚨 HIDROALERT — NIVEL {decision.level}",
        f"📍 Zona: {result.aoi_name}",
        f"🌧️ Escenario: {result.scenario_label}",
        f"💧 Volumen desbordado: {hid['water_volume_m3']:,.0f} m³",
        f"🌊 Área inundada: {hid['flooded_area_ha']:.1f} ha (lámina máx. {hid['max_depth_m']:.2f} m)",
        f"🏠 Viviendas afectadas: {result.impact.buildings_affected}",
        f"🚧 Vías bloqueadas: {result.impact.roads_blocked}",
    ]
    if decision.level == "ROJO":
        lines.append("⛔ ORDEN: EVACUACIÓN INMEDIATA a zonas altas.")
    elif decision.level == "AMARILLO":
        lines.append("⚠️ ORDEN: Precaución; monitoreo continuo y listo para evacuar.")
    else:
        lines.append("✅ Situación normal.")
    lines.append(f"🕒 {result.timestamp}")
    return "\n".join(lines)


def send_emergency_notifications(
    result: SimulationResult,
    decision: AlertDecision,
    force_all_levels: bool = False,
) -> dict[str, Any]:
    """
    Pipeline completo de notificación (Módulo 4, entregable).

    1. Compone el mensaje y payload JSON.
    2. Envía SMS/WhatsApp por Twilio.
    3. Publica en el webhook COER.

    Args:
        result:            resultado de la simulación.
        decision:          decisión del motor de alertas.
        force_all_levels:  si True notifica también en VERDE (útil en pruebas).

    Returns:
        dict con el payload enviado y el resultado por canal.
    """
    if decision.level == "VERDE" and not force_all_levels:
        logger.info("Nivel VERDE: no se emiten notificaciones.")
        return {"skipped": True, "reason": "nivel VERDE"}

    message = compose_alert_message(result, decision)
    payload = build_alert_payload(result, decision)
    twilio_results = send_twilio_messages(message)
    webhook_ok = send_webhook_coer(payload)
    return {
        "skipped": False,
        "message": message,
        "payload": payload,
        "twilio": twilio_results,
        "webhook_ok": webhook_ok,
    }
