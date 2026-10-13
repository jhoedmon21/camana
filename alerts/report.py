"""
report.py — Informe automático PDF/JSON (Módulo 4).

Genera:
    1. Un JSON completo (payload de emergencia) — contrat de integración.
    2. Un PDF con: encabezado del nivel de alerta, resumen hidrológico,
       matriz de impacto, razones del motor y el mapa estático recortado
       de la zona (Google Maps Static si hay API key; si no, render local
       con matplotlib de la lámina simulada).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from hidroalert.config import CONFIG, REPORTS_DIR
from hidroalert.models import SimulationResult, AlertDecision
from hidroalert.alerts.notifier import build_alert_payload
from hidroalert.data_ingest.static_map import fetch_static_map_png

logger = logging.getLogger(__name__)

# Colores institucionales por nivel de alerta
LEVEL_COLORS = {
    "VERDE": (46, 139, 87),
    "AMARILLO": (243, 184, 6),
    "ROJO": (192, 57, 43),
}


def _render_local_map_png(result: SimulationResult, out_path: Path) -> Path | None:
    """
    Render local de la lámina simulada (fallback sin Google Maps API).

    Dibuja la máscara de inundación sobre el terreno (HAND) con matplotlib
    y guarda un PNG.
    """
    try:
        import matplotlib

        matplotlib.use("Agg")  # backend sin GUI para servidores
        import matplotlib.pyplot as plt
        from matplotlib.colors import LinearSegmentedColormap
    except ImportError:
        logger.warning("matplotlib no disponible; informe sin mapa local.")
        return None

    fig, ax = plt.subplots(figsize=(6, 6), dpi=120)
    hand = np.nan_to_num(result.depth_m, nan=np.nan)
    base = ax.imshow(hand, cmap="terrain", origin="upper")
    flood_rgba = np.zeros((*result.flood_mask.shape, 4))
    flood_rgba[result.flood_mask] = (0.10, 0.35, 0.85, 0.75)
    ax.imshow(flood_rgba, origin="upper")
    ax.set_title(f"Lámina simulada — {result.aoi_name}\n{result.scenario_label}")
    ax.axis("off")
    fig.colorbar(base, ax=ax, label="HAND (m)", shrink=0.8)
    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)
    return out_path


def generate_alert_report(
    result: SimulationResult,
    decision: AlertDecision,
    out_dir: Path | None = None,
) -> dict[str, Path | None]:
    """
    Genera el informe automático de alerta (PDF + JSON + mapa PNG).

    Args:
        result:   simulación que dispara la alerta.
        decision: decisión del motor condicional.
        out_dir:  carpeta destino (por defecto hidroalert/reports/).

    Returns:
        dict con rutas generadas: {'json', 'pdf', 'map_png'} (valores None si falló).
    """
    out_dir = Path(out_dir) if out_dir else REPORTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    level = decision.level

    # ---------- JSON ----------
    payload = build_alert_payload(result, decision)
    json_path = out_dir / f"informe_{level.lower()}_{stamp}.json"
    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )

    # ---------- Mapa ----------
    min_lon, min_lat, max_lon, max_lat = result.bbox
    center_lat = (min_lat + max_lat) / 2
    center_lon = (min_lon + max_lon) / 2
    # Zoom adaptado al tamaño del AOI (más grande => menos zoom)
    import math

    span_km = max(
        (max_lon - min_lon) * 111.32 * math.cos(math.radians(center_lat)),
        (max_lat - min_lat) * 110.57,
    )
    zoom = max(10, min(15, int(8.5 - math.log2(span_km + 1e-6))))
    map_png = fetch_static_map_png(
        center_lat=center_lat,
        center_lon=center_lon,
        zoom=zoom,
        out_path=out_dir / f"mapa_{level.lower()}_{stamp}.png",
    )
    if map_png is None:
        map_png = _render_local_map_png(result, out_dir / f"mapa_local_{level.lower()}_{stamp}.png")

    # ---------- PDF ----------
    pdf_path = out_dir / f"informe_{level.lower()}_{stamp}.pdf"
    try:
        _write_pdf(result, decision, pdf_path, map_png)
    except Exception as exc:
        logger.error("No se pudo generar el PDF: %s", exc)
        pdf_path = None

    logger.info("Informe generado: %s | %s | %s", json_path, pdf_path, map_png)
    return {"json": json_path, "pdf": pdf_path, "map_png": map_png}


def _latin1(text: str) -> str:
    """Sanea texto para fuentes core de fpdf2 (latin-1)."""
    return text.encode("latin-1", "replace").decode("latin-1")


def _write_pdf(
    result: SimulationResult,
    decision: AlertDecision,
    pdf_path: Path,
    map_png: Path | None,
) -> None:
    """Escribe el PDF con fpdf2 (fuentes core latin-1)."""
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    hid = result.to_dict()["hydrology"]
    r, g, b = LEVEL_COLORS[decision.level]

    def _line(pdf, h: float, text: str, *, bold: bool = False, size: int = 11, fill=None) -> None:
        """Escribe una línea (cell) avanzando a la línea siguiente."""
        if fill is not None:
            pdf.set_fill_color(*fill)
        pdf.set_font("Helvetica", "B" if bold else "", size)
        pdf.cell(
            0, h, _latin1(text), fill=fill is not None,
            new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        )

    pdf = FPDF()
    pdf.add_page()

    # Encabezado con banda de color por nivel
    pdf.set_text_color(255, 255, 255)
    _line(pdf, 14, f"HIDROALERT — ALERTA {decision.level}", bold=True, size=20, fill=(r, g, b))
    pdf.set_text_color(0, 0, 0)
    _line(pdf, 8, f"Zona: {result.aoi_name}")
    _line(pdf, 8, f"Generado: {result.timestamp}")
    pdf.ln(4)

    # Escenario simulado
    _line(pdf, 8, "Escenario simulado", bold=True, size=13)
    _line(pdf, 7, f"Precipitación: {result.precipitation_mm_h:.0f} mm/h")
    _line(pdf, 7, f"Incremento de caudal: +{result.flow_increase_pct:.0f} %")
    pdf.ln(2)

    # Resumen hidrológico
    _line(pdf, 8, "Resumen hidrológico", bold=True, size=13)
    _line(pdf, 7, f"Volumen desbordado: {hid['water_volume_m3']:,.0f} m3 "
                   f"({hid['water_volume_thousand_lits']:,.0f} miles de litros)")
    _line(pdf, 7, f"Área inundada: {hid['flooded_area_ha']:.1f} ha")
    _line(pdf, 7, f"Lámina máxima: {hid['max_depth_m']:.2f} m")
    _line(pdf, 7, f"Agua observada SAR (referencia): {result.observed_water_area_m2/1e4:.1f} ha")
    pdf.ln(2)

    # Matriz de impacto
    imp = result.impact
    _line(pdf, 8, "Matriz de impacto", bold=True, size=13)
    _line(pdf, 7, f"Viviendas/edificios afectados: {imp.buildings_affected} de {imp.buildings_total}")
    _line(pdf, 7, f"Vías bloqueadas: {imp.roads_blocked} de {imp.roads_total}")
    _line(pdf, 7, f"Hectáreas agrícolas sumergidas: {imp.farmland_flooded_ha:.1f} ha")
    pdf.ln(2)

    # Razones de la decisión
    _line(pdf, 8, "Razones del motor de alertas", bold=True, size=13)
    pdf.set_font("Helvetica", "", 10)
    for reason in decision.reasons:
        pdf.multi_cell(0, 6, _latin1(f"- {reason}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Mapa
    if map_png and Path(map_png).exists():
        pdf.add_page()
        _line(pdf, 8, "Mapa de la zona de desastre", bold=True, size=13)
        try:
            pdf.image(str(map_png), x=15, w=180)
        except Exception as exc:
            _line(pdf, 8, f"(No se pudo incrustar el mapa: {exc})")

    pdf.output(str(pdf_path))


def _append_image_page(pdf_path: Path, image_path: Path, title: str) -> None:
    """
    Añade una página final con una imagen (p. ej. captura 3D de Cesium)
    a un PDF ya generado usando pypdf. Si pypdf no está disponible,
    deja la captura como PNG adjunto (degradación suave).
    """
    if not image_path.exists():
        return
    try:
        from fpdf import FPDF
        from fpdf.enums import XPos, YPos
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        logger.warning("pypdf no instalado; la captura 3D queda como PNG adjunto.")
        return

    # Página nueva con la imagen
    tmp_pdf = image_path.parent / "_tmp_page.pdf"
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, _latin1(title), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    try:
        pdf.image(str(image_path), x=10, w=190)
    except Exception as exc:
        pdf.cell(0, 8, _latin1(f"(No se pudo incrustar: {exc})"),
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.output(str(tmp_pdf))

    # Merge: documento original + página de la captura
    writer = PdfWriter()
    for page in PdfReader(str(pdf_path)).pages:
        writer.add_page(page)
    for page in PdfReader(str(tmp_pdf)).pages:
        writer.add_page(page)
    with open(pdf_path, "wb") as fh:
        writer.write(fh)
    tmp_pdf.unlink(missing_ok=True)
