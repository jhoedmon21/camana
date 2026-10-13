"""Módulo 4 — Sistema automatizado de alertas, notificaciones y reportes."""

from hidroalert.alerts.engine import evaluate_alert
from hidroalert.alerts.notifier import send_emergency_notifications
from hidroalert.alerts.report import generate_alert_report

__all__ = ["evaluate_alert", "send_emergency_notifications", "generate_alert_report"]
