"""
app.py — Dashboard interactivo de HidroAlert (Módulo 3) · v2 rediseñado.

Mejoras de la v2:
    * Pestañas: Simulador · Pronóstico 48 h · Datos & Método · Acerca de.
    * Datos REALES de Google Earth Engine por defecto (Sentinel-1 + HAND +
      edificios) si el proyecto GEE está registrado; fallback a demo.
    * Mapa con lámina de agua coloreada POR PROFUNDIDAD (no un solo azul),
      leyenda, edificios afectados y vías bloqueadas.
    * Selector de escenario como segmented control + sliders finos.
    * Pestaña de pronóstico: timeline 48 h coloreada por nivel de alerta,
      usando Open-Meteo (o WeatherNext 3 con key).

Ejecutar:
    streamlit run hidroalert/dashboard/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Bootstrap: permite `streamlit run hidroalert/dashboard/app.py` desde cualquier cwd
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import numpy as np
import plotly.graph_objects as go
import streamlit as st
import folium
from folium.plugins import Fullscreen, MiniMap, MeasureControl
from streamlit_folium import st_folium

from hidroalert import __version__
from hidroalert.config import CONFIG, BANKFULL_DEPTH_M
from hidroalert.data_ingest.aoi import (
    DEFAULT_AOI,
    parse_bbox_text,
    list_zones,
    resolve_aoi,
)
from hidroalert.data_ingest.gee_client import is_available
from hidroalert.data_ingest.ingest_service import build_area_snapshot, build_demo_snapshot
from hidroalert.data_ingest.forecast import forecast_precipitation
from hidroalert.hydrology.simulation_engine import simulate_flood, scenario_presets
from hidroalert.config import bankfull_for_zone
from hidroalert.hydrology.timeline import build_alert_timeline
from hidroalert.alerts.engine import evaluate_alert
from hidroalert.alerts.notifier import compose_alert_message, send_emergency_notifications
from hidroalert.alerts.report import generate_alert_report
from hidroalert.models import AreaSnapshot
from hidroalert.dashboard import scene3d

# ---------------------------------------------------------------------------
# Página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="HidroAlert · Alerta Temprana de Inundaciones",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

NIVEL_COLOR = {"VERDE": "#2e7d32", "AMARILLO": "#f9a825", "ROJO": "#c62828"}
NIVEL_ICON = {"VERDE": "✅", "AMARILLO": "⚠️", "ROJO": "🚨"}
PRESET_ICON = {
    "Lluvia Ligera": "💧",
    "Moderada": "🌧️",
    "Torrencial / FEN Extremo": "⛈️",
}

# ---------------------------------------------------------------------------
# Carga de datos
# ---------------------------------------------------------------------------
@st.cache_resource(show_spinner="🛰️ Descargando Sentinel-1 + HAND + edificios desde Earth Engine…")
def load_snapshot_real(zone_key: str) -> AreaSnapshot:
    """Snapshot GEE real para una zona (id del registro) o bbox personalizado."""
    aoi = resolve_aoi(zone_key)
    return build_area_snapshot(aoi, lookback_days=12)


@st.cache_resource(show_spinner="Generando área demo…")
def load_snapshot_demo() -> AreaSnapshot:
    return build_demo_snapshot()


@st.cache_data(ttl=1800, show_spinner="🌦️ Consultando pronóstico horario…")
def load_forecast(zone_key: str, hours: int) -> dict:
    aoi = resolve_aoi(zone_key)
    return forecast_precipitation(aoi, hours=hours)


# ---------------------------------------------------------------------------
# Geometría → GeoJSON
# ---------------------------------------------------------------------------
def _grid_geojson(
    mask: np.ndarray,
    bbox,
    prop: str,
    depth: np.ndarray | None = None,
    max_cells: int = 5000,
) -> dict:
    """
    Convierte una máscara booleana en GeoJSON de celdas (limitado a max_cells).

    Si se pasa `depth`, cada feature recibe `dclass`: 0 (0–0.3 m),
    1 (0.3–0.8 m) o 2 (>0.8 m) para colorear la lámina por profundidad.
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    nrows, ncols = mask.shape
    dlon = (max_lon - min_lon) / ncols
    dlat = (max_lat - min_lat) / nrows
    rows, cols = np.nonzero(mask)
    step = max(1, len(rows) // max_cells)
    feats = []
    for r, c in zip(rows[::step], cols[::step]):
        lat1 = max_lat - r * dlat
        lon0 = min_lon + c * dlon
        props = {prop: True}
        if depth is not None:
            d = float(depth[r, c])
            props["dclass"] = 2 if d > 0.8 else (1 if d > 0.3 else 0)
            props["d_mm"] = round(d * 100)
        feats.append({
            "type": "Feature",
            "properties": props,
            "geometry": {"type": "Polygon", "coordinates": [[
                [lon0, lat1 - dlat], [lon0 + dlon, lat1 - dlat],
                [lon0 + dlon, lat1], [lon0, lat1], [lon0, lat1 - dlat],
            ]]},
        })
    return {"type": "FeatureCollection", "features": feats}


# Paleta por clase de profundidad (0: poco profundo, 1: peligro, 2: severo)
_DCLASS_STYLE = {
    0: {"fillColor": "#81d4fa", "color": "#81d4fa", "weight": 0, "fillOpacity": 0.55},
    1: {"fillColor": "#1e88e5", "color": "#1e88e5", "weight": 0, "fillOpacity": 0.65},
    2: {"fillColor": "#0d47a1", "color": "#0d47a1", "weight": 0, "fillOpacity": 0.8},
}


# ---------------------------------------------------------------------------
# Barra lateral
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown(
        f"""
        <div style="text-align:center;padding:6px 0 2px 0">
          <h2 style="margin:0">🌊 HidroAlert</h2>
          <p style="margin:2px 0 0 0;color:#888;font-size:.85em">
             v{__version__} · jhons-workspace-amus9
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()

    st.subheader("📍 Área de análisis")
    gee_ok = is_available()
    fuente = st.toggle(
        "🛰️ Usar datos reales (Earth Engine)",
        value=gee_ok,
        disabled=not gee_ok,
        help="Sentinel-1 + HAND (MERIT Hydro) + edificios. Si está apagado se usa el área demo sintética."
        if gee_ok else "Earth Engine no disponible: configure HIDROALERT_GEE_PROJECT_ID",
    )

    # --- Selector multi-zona (quebradas/sectores registrados) ---
    zonas = list_zones()
    zone_labels = {z["id"]: f"{z['name']}" for z in zonas}
    sel = st.selectbox(
        "Zona de vigilancia",
        options=[z["id"] for z in zonas],
        format_func=lambda zid: zone_labels[zid],
        index=0,
        help="Presets de quebradas y tramos de río. Incluye su zona por coordenadas abajo.",
    )
    st.session_state.setdefault("zone", sel)
    if sel != st.session_state["zone"]:
        st.session_state["zone"] = sel
        st.toast(f"Zona cambiada: {zone_labels[sel]}")

    modo_bbox = st.checkbox("Coordenadas personalizadas", value=False,
                            help="Analiza cualquier otra zona con un bbox WGS84")
    if modo_bbox:
        bbox_text = st.text_input(
            "BBox (min_lon,min_lat,max_lon,max_lat)",
            value=",".join(str(round(v, 4)) for v in DEFAULT_AOI.bbox),
        )
        try:
            parse_bbox_text(bbox_text)
        except ValueError as e:
            st.error(f"BBox inválido: {e}")
        zone_key = bbox_text
    else:
        zone_key = st.session_state["zone"]

    st.divider()
    st.subheader("🎛️ Escenario")
    presets = scenario_presets()
    preset = st.segmented_control(
        "Escenarios predefinidos",
        options=list(presets.keys()),
        selection_mode="single",
        default="Moderada",
        format_func=lambda k: f"{PRESET_ICON.get(k, '')} {k.split(' / ')[0]}",
    )
    preset = preset or "Moderada"
    p = presets[preset]
    precip = st.slider(
        "🌧️ Precipitación (mm/h)", 0.0, 200.0, float(p["precipitation_mm_h"]), 5.0,
        help="Intensidad horaria de lluvia sobre la cuenca.",
    )
    caudal = st.slider(
        "📈 Incremento de caudal (%)", 0, 300, int(p["flow_increase_pct"]), 10,
        help="Aumento del caudal del río/quebrada respecto a condiciones base.",
    )
    overland = st.toggle(
        "💧 Concentración de agua sobre terreno",
        value=False,
        help="Escorrentía superficial (ruteo D8 sobre el DEM): la lluvia fluye "
             "celda a celda cuesta abajo y se acumula en las depresiones del "
             "terreno, además del desborde del cauce. El pronóstico 48 h la "
             "incorpora siempre.",
    )

    st.caption(f"⚖️ Bankfull del cauce: **{BANKFULL_DEPTH_M:.2f} m** (configurable por quebrada)")

    st.divider()
    with st.expander("🔌 Estado de integraciones"):
        st.markdown(
            f"""
            | Servicio | Estado |
            |---|---|
            | Earth Engine | {'🟢' if gee_ok else '🔴 demo'} |
            | Pronóstico | {'🟢 WeatherNext' if CONFIG.forecast.is_configured else '🟢 Open-Meteo'} |
            | Twilio | {'🟢' if CONFIG.twilio.is_configured else '🔴'} |
            | Webhook COER | {'🟢' if CONFIG.webhook.is_configured else '🔴'} |
            """,
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------------
# Snapshot (real o demo) — cacheado
# ---------------------------------------------------------------------------
try:
    if fuente:
        snapshot = load_snapshot_real(zone_key)
        # Etiqueta legible de la zona activa (preset o coordenadas)
        st.session_state["zone_name"] = resolve_aoi(zone_key).name
    else:
        snapshot = load_snapshot_demo()
except Exception as exc:
    st.error(f"**Earth Engine falló:** {exc}")
    st.info("Continuando con el área demo. Revise su conexión o credenciales.")
    snapshot = load_snapshot_demo()

fuente_label = "🛰️ GEE real" if fuente else "🧪 Demo"

# ---------------------------------------------------------------------------
# Pestañas
# ---------------------------------------------------------------------------
tab_sim, tab_3d, tab_pron, tab_coe, tab_met, tab_acerca = st.tabs(
    ["🎯 Simulador", "🏙️ Vista 3D", "🌦️ Pronóstico 48 h",
     "🚨 COE — Centro de Observación", "📚 Datos & Método", "ℹ️ Acerca de"]
)

# ===========================================================================
# TAB 1 — SIMULADOR
# ===========================================================================
with tab_sim:
    result = simulate_flood(
        snapshot, precipitation_mm_h=precip, flow_increase_pct=caudal,
        scenario_label=preset,
        bankfull_depth_m=bankfull_for_zone(zone_key, snapshot.aoi_name),
        include_overland=overland,
    )
    decision = evaluate_alert(result)
    nivel = decision.level
    color = NIVEL_COLOR[nivel]
    icon = NIVEL_ICON[nivel]
    hid = result.to_dict()["hydrology"]

    # --- Banner de alerta
    st.markdown(
        f"""
        <div style="padding:14px 20px;border-radius:12px;background:{color};color:#fff;
                    display:flex;justify-content:space-between;align-items:center;">
          <div>
            <h2 style="margin:0">{icon} NIVEL {nivel}</h2>
            <p style="margin:2px 0 0 0;opacity:.95">{decision.reasons[0]}</p>
          </div>
          <div style="text-align:right;font-size:.9em;opacity:.9">
            <div><b>{snapshot.aoi_name}</b></div>
            <div>{fuente_label} · {precip:.0f} mm/h · +{caudal:.0f}% caudal</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

    # --- KPIs como tarjetas HTML (sin truncamiento, control total de estilo)
    def _vol_txt(v: float) -> str:
        if v >= 1e6:
            return f"{v/1e6:.2f} M m³"
        if v >= 1e3:
            return f"{v/1e3:.0f} k m³"
        return f"{v:,.0f} m³"

    def _kpi_card(emoji: str, label: str, value: str, sub: str = "", accent: str = "#1565c0") -> str:
        sub_html = (
            f'<div style="font-size:.72em;opacity:.65;margin-top:2px">{sub}</div>'
            if sub else ""
        )
        return (
            f'<div style="background:rgba(127,127,127,.08);border-radius:10px;'
            f'border-left:4px solid {accent};padding:10px 12px;margin:2px">'
            f'<div style="font-size:.78em;opacity:.75;white-space:nowrap">{emoji} {label}</div>'
            f'<div style="font-size:1.4em;font-weight:700;white-space:nowrap">{value}</div>'
            f'{sub_html}</div>'
        )

    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(_kpi_card("💧", "Volumen", _vol_txt(hid["water_volume_m3"]),
                              accent="#1e88e5"), unsafe_allow_html=True)
    with k2:
        st.markdown(_kpi_card("🌊", "Área inundada", f"{hid['flooded_area_ha']:,.1f} ha",
                              accent="#00acc1"), unsafe_allow_html=True)
    with k3:
        st.markdown(_kpi_card("📏", "Lámina máx.", f"{hid['max_depth_m']:.2f} m",
                              accent="#8e24aa"), unsafe_allow_html=True)
    with k4:
        st.markdown(_kpi_card("🏠", "Viviendas", f"{result.impact.buildings_affected}",
                              f"de {result.impact.buildings_total} mapeadas",
                              accent="#e53935"), unsafe_allow_html=True)
    with k5:
        st.markdown(_kpi_card("🚧", "Vías bloqueadas", f"{result.impact.roads_blocked}",
                              f"de {result.impact.roads_total} mapeadas",
                              accent="#fb8c00"), unsafe_allow_html=True)
    if overland:
        st.markdown(
            _kpi_card(
                "🌧️", "Escorrentía sobre terreno", _vol_txt(hid["overland_volume_m3"]),
                f"{hid['overland_area_ha']:,.1f} ha con pozas · "
                f"lámina máx {hid['overland_max_depth_m']:.2f} m",
                accent="#00897b",
            ),
            unsafe_allow_html=True,
        )
    st.write("")

    # --- Mapa + panel derecho
    col_mapa, col_panel = st.columns([2.6, 1.1], gap="medium")

    with col_mapa:
        mask_bytes = result.flood_mask.tobytes()
        center = [(result.bbox[1] + result.bbox[3]) / 2, (result.bbox[0] + result.bbox[2]) / 2]
        fmap = folium.Map(location=center, zoom_start=13, tiles=None, control_scale=True)

        folium.TileLayer(
            tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
            attr="Google Satellite", name="Google Satellite", show=True,
        ).add_to(fmap)
        folium.TileLayer("OpenStreetMap", name="OpenStreetMap", show=False).add_to(fmap)

        # Agua observada SAR (referencia)
        if snapshot.flood_mask_observed is not None and snapshot.flood_mask_observed.any():
            obs = _grid_geojson(snapshot.flood_mask_observed, snapshot.bbox, prop="obs",
                                max_cells=2500)
            folium.GeoJson(
                obs, name="Agua observada (SAR)",
                style_function=lambda f: {"fillColor": "#7FDBFF", "color": "#7FDBFF",
                                          "weight": 0, "fillOpacity": 0.4},
                show=True,
            ).add_to(fmap)

        # Lámina simulada coloreada POR PROFUNDIDAD con tooltip de centímetros
        # (solo si hay celdas inundadas: GeoJsonTooltip falla con colecciones vacías)
        fc_inund = _grid_geojson(result.flood_mask, result.bbox, prop="flood",
                                 depth=result.depth_m)
        if fc_inund["features"]:
            folium.GeoJson(
                fc_inund,
                name="Inundación simulada (por profundidad)",
                style_function=lambda f: _DCLASS_STYLE[
                    f["properties"].get("dclass", 0)
                ],
                tooltip=folium.GeoJsonTooltip(
                    fields=["d_mm"], aliases=["Lámina (cm):"], localize=True),
                show=True,
            ).add_to(fmap)

        # Vías bloqueadas
        if snapshot.roads:
            for feat in snapshot.roads["features"]:
                rid = feat.get("properties", {}).get("road_id", feat.get("id"))
                blocked = any(d.road_id == rid and d.blocked
                              for d in result.impact.roads_detail)
                if blocked:
                    folium.GeoJson(
                        feat, name=f"🚧 {rid}",
                        style_function=lambda f: {"color": "#ff6d00", "weight": 5},
                    ).add_to(fmap)

        # Edificios afectados
        for b in result.impact.buildings_detail[:80]:
            folium.CircleMarker(
                location=(b.centroid[1], b.centroid[0]), radius=5,
                color="#c62828", fill=True, fill_opacity=0.9,
                tooltip=f"Lámina: {b.depth_m:.2f} m",
            ).add_to(fmap)

        # Leyenda
        leyenda = """
        <div style="position:fixed;bottom:30px;left:30px;z-index:9999;background:white;
                    padding:10px 14px;border-radius:8px;box-shadow:0 2px 6px rgba(0,0,0,.3);
                    font-size:13px;line-height:1.7">
          <b>Lámina de agua</b><br>
          <span style="display:inline-block;width:14px;height:14px;background:#81d4fa;margin-right:6px"></span>0 – 0.3 m (poco profundo)<br>
          <span style="display:inline-block;width:14px;height:14px;background:#1e88e5;margin-right:6px"></span>0.3 – 0.8 m (peligro)<br>
          <span style="display:inline-block;width:14px;height:14px;background:#0d47a1;margin-right:6px"></span>&gt; 0.8 m (severo)<br>
          <span style="display:inline-block;width:14px;height:14px;background:#ff6d00;margin-right:6px"></span>Vía bloqueada<br>
          <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#c62828;margin-right:8px"></span>Vivienda afectada
        </div>
        """
        fmap.get_root().html.add_child(folium.Element(leyenda))

        folium.LayerControl(collapsed=True).add_to(fmap)
        Fullscreen().add_to(fmap)
        MiniMap(toggle_display=True).add_to(fmap)
        MeasureControl().add_to(fmap)
        st_folium(fmap, height=540, returned_objects=[], use_container_width=True)

    with col_panel:
        # Gauge de volumen
        um_am = CONFIG.thresholds.volume_yellow_m3
        um_ro = CONFIG.thresholds.volume_red_m3
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=hid["water_volume_m3"],
            number={"valueformat": ",.0f"},
            title={"text": "Volumen (m³)"},
            gauge={
                "axis": {"range": [0, max(um_ro * 1.5, hid["water_volume_m3"] * 1.2)]},
                "bar": {"color": color},
                "steps": [
                    {"range": [0, um_am], "color": "#e8f5e9"},
                    {"range": [um_am, um_ro], "color": "#fff8e1"},
                    {"range": [um_ro, max(um_ro * 1.5, hid["water_volume_m3"] * 1.2)], "color": "#ffebee"},
                ],
                "threshold": {"line": {"color": "#c62828", "width": 3}, "value": um_ro},
            },
        ))
        fig.update_layout(height=220, margin=dict(l=5, r=5, t=30, b=5))
        st.plotly_chart(fig, use_container_width=True)

        # Impacto
        fig2 = go.Figure(go.Bar(
            x=["Viviendas", "Vías"],
            y=[result.impact.buildings_affected, result.impact.roads_blocked],
            marker_color=["#c62828", "#ff6d00"],
            text=[result.impact.buildings_affected, result.impact.roads_blocked],
            textposition="outside",
        ))
        fig2.update_layout(height=200, margin=dict(l=5, r=5, t=30, b=5),
                           title="Infraestructura")
        st.plotly_chart(fig2, use_container_width=True)

        # Sensibilidad
        flows = np.linspace(0, 300, 21)
        _bf = bankfull_for_zone(zone_key, snapshot.aoi_name)
        vols = [simulate_flood(snapshot, precip, float(f), fast_mode=True,
                               bankfull_depth_m=_bf).water_volume_m3
                for f in flows]
        fig3 = go.Figure(go.Scatter(
            x=flows, y=vols, mode="lines", fill="tozeroy",
            line={"color": "#1565c0", "shape": "spline"},
        ))
        fig3.add_vline(x=caudal, line_dash="dash", line_color="#c62828",
                       annotation_text="actual")
        fig3.update_layout(height=210, margin=dict(l=5, r=5, t=30, b=5),
                           title="Sensibilidad al caudal",
                           xaxis_title="% caudal", yaxis_title="m³")
        st.plotly_chart(fig3, use_container_width=True)

    # --- Detalle y acciones
    with st.expander("🧠 Razones del motor de alertas", expanded=(nivel != "VERDE")):
        for razon in decision.reasons:
            st.markdown(f"- {razon}")

    cA, cB, _ = st.columns([1, 1, 2])
    with cA:
        if st.button("📨 Notificar (Twilio + COER)", use_container_width=True,
                     disabled=not (CONFIG.twilio.is_configured or CONFIG.webhook.is_configured)):
            out = send_emergency_notifications(result, decision, force_all_levels=True)
            st.success("Notificaciones enviadas." if not out.get("skipped") else "Nivel VERDE: omitido.")
    with cB:
        if st.button("🧾 Generar informe PDF", use_container_width=True):
            with st.spinner("Generando…"):
                paths = generate_alert_report(result, decision)
            ok = {k: v for k, v in paths.items() if v}
            st.success("Generado: " + ", ".join(f"{k}→{Path(v).name}" for k, v in ok.items()))

# ===========================================================================
# TAB 1b — VISTA 3D (PyDeck / deck.gl)
# ===========================================================================
with tab_3d:
    st.subheader("🏙️ Ciudad 3D — edificios extruidos + lámina de inundación")
    st.caption(
        "Vista tipo COE: las construcciones (GEE) se levantan en 3D y se pintan "
        "**rojas si quedan afectadas** por la lámina simulada. El agua se muestra "
        "sobre el suelo satelital con su clase de profundidad."
    )
    c3d1, c3d2 = st.columns(2, gap="medium")
    with c3d1:
        st.markdown("**🏙️ Ciudad extruida**")
        try:
            st.pydeck_chart(scene3d.city_scene(snapshot, result, height=520),
                            use_container_width=True)
        except Exception as exc:
            st.error(f"Vista 3D no disponible: {exc}")
    with c3d2:
        st.markdown("**🌊 Columnas de lámina de agua** (altura exagerada ×12)")
        try:
            st.pydeck_chart(
                scene3d.water_surface_scene(snapshot, result, height=520),
                use_container_width=True,
            )
        except Exception as exc:
            st.error(f"Vista 3D no disponible: {exc}")

    leyenda3d = (
        '<div style="display:flex;gap:18px;font-size:.85em;padding:6px 2px;flex-wrap:wrap">'
        '<span>🧱 Gris: edificio fuera de riesgo</span>'
        '<span style="color:#e53935">🧱 Rojo: vivienda afectada (lámina ≥ 15 cm)</span>'
        '<span style="color:#81d4fa">🔵 Agua 0–30 cm</span>'
        '<span style="color:#1e88e5">🔵 Agua 30–80 cm</span>'
        '<span style="color:#0d47a1">🔵 Agua &gt; 80 cm</span>'
        '</div>'
    )
    st.markdown(leyenda3d, unsafe_allow_html=True)

# ===========================================================================
# TAB 2 — PRONÓSTICO 48 h
# ===========================================================================
with tab_pron:
    st.subheader("🌦️ Línea de tiempo de alertas — próximas 48 horas")
    st.caption(
        "Cada hora del pronóstico se propaga por el motor hidrológico —"
        "incluida la concentración de agua sobre el terreno (escorrentía D8)— "
        "para predecir **cuándo** el nivel sube (paradigma WeatherNext 3 "
        "aplicado a inundaciones)."
    )
    try:
        fc = load_forecast(zone_key, 48)  # cacheado 30 min
        st.info(f"Fuente: **{fc['source']}** · pico previsto: **{fc['peak_mm_h']:.1f} mm/h** "
                f"a las {fc['peak_time'][11:16]} UTC")
        with st.spinner("Propagando 48 horas por el motor hidrológico…"):
            tl = build_alert_timeline(
                snapshot, fc, max_hours=48,
                bankfull_depth_m=bankfull_for_zone(zone_key, snapshot.aoi_name),
            )

        # --- Timeline coloreada por nivel
        times = [t["time"][11:16] for t in tl["timeline"]]
        vols = [t["volume_m3"] for t in tl["timeline"]]
        lluvias = [t["mm_h"] for t in tl["timeline"]]
        niveles = [t["level"] for t in tl["timeline"]]
        colors = [NIVEL_COLOR[n] for n in niveles]

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=times, y=lluvias, marker_color="#90a4ae", opacity=0.5,
            name="Lluvia (mm/h)", yaxis="y2",
        ))
        fig.add_trace(go.Bar(
            x=times, y=vols, marker_color=colors, name="Volumen (m³)",
            customdata=[[n, b] for n, b in zip(niveles, [t["buildings"] for t in tl["timeline"]])],
            hovertemplate="%{x}<br>Nivel: %{customdata[0]}<br>Volumen: %{y:,.0f} m³"
                          "<br>Viviendas: %{customdata[1]}<extra></extra>",
        ))
        fig.update_layout(
            height=340, barmode="overlay",
            margin=dict(l=10, r=10, t=30, b=10),
            yaxis={"title": "Volumen (m³)"},
            yaxis2={"title": "Lluvia (mm/h)", "overlaying": "y", "side": "right",
                    "showgrid": False},
            xaxis={"title": "Hora UTC", "categoryorder": "category ascending"},
            legend={"orientation": "h", "y": 1.12},
        )
        st.plotly_chart(fig, use_container_width=True)

        # --- Cruces de nivel
        c1, c2 = st.columns(2)
        if "AMARILLO" in tl["rise_to"]:
            c1.warning(f"⚠️ Primer cruce a **AMARILLO**: {tl['rise_to']['AMARILLO'][:16]} UTC")
        else:
            c1.success("✅ Sin cruce a AMARILLO en 48 h")
        if "ROJO" in tl["rise_to"]:
            c2.error(f"🚨 Primer cruce a **ROJO**: {tl['rise_to']['ROJO'][:16]} UTC")
        else:
            c2.success("✅ Sin cruce a ROJO en 48 h")

        with st.expander("📋 Tabla horaria completa"):
            import pandas as pd
            df = pd.DataFrame(tl["timeline"])
            df = df[["time", "mm_h", "level", "volume_m3", "overland_volume_m3",
                     "flooded_ha", "buildings"]]
            df.columns = ["Hora (UTC)", "Lluvia (mm/h)", "Nivel", "Volumen (m³)",
                          "Escorrentía (m³)", "Área (ha)", "Viviendas"]
            st.dataframe(df, use_container_width=True, height=320)
    except Exception as exc:
        st.error(f"No se pudo obtener el pronóstico: {exc}")
        st.caption("Verifique su conexión a internet (Open-Meteo es gratuito y no requiere key).")

# ===========================================================================
# TAB 3b — COE: CENTRO DE OBSERVACIÓN DE EMERGENCIAS
# ===========================================================================
with tab_coe:
    st.subheader("🚨 COE — Centro de Observación de Emergencias")
    st.caption(
        "Sala situacional para Defensa Civil / COER: estado consolidado por "
        "cuenca, bitácora de incidentes, protocolos de activación y boletín."
    )

    # ---------- Estado consolidado del evento actual ----------
    now_iso = result.timestamp[:16].replace("T", " ")
    nivel = decision.level
    colA, colB, colC, colD = st.columns(4)
    colA.metric("Nivel actual", f"{NIVEL_ICON[nivel]} {nivel}",
                f"{now_iso} UTC", border=True)
    colB.metric("Viviendas en riesgo", f"{result.impact.buildings_affected}",
                f"de {result.impact.buildings_total} expuestas", border=True)
    colC.metric("Vías cortadas", f"{result.impact.roads_blocked}",
                f"de {result.impact.roads_total}", border=True)
    colD.metric("Agua observada SAR", f"{snapshot.observed_water_area_m2/1e4:.0f} ha",
                "último pase Sentinel-1", border=True)

    st.divider()

    # ---------- Mapa de cuencas vigiladas (mini tabla operativa) ----------
    left, right = st.columns([1.4, 1], gap="medium")
    with left:
        st.markdown("#### 🛡️ Cuencas vigiladas")
        cuencas = [
            {"Cuenca": "Quebrada Canto Grande — Rímac inf.", "Punto crítico": "Jicamarca–Bayóvar",
             "Nivel": nivel, "Tendencia": "⬆️ si persiste lluvia"},
            {"Cuenca": "Río Rímac (tramo bajo)", "Punto crítico": "Puente del Ejército",
             "Nivel": nivel, "Tendencia": "según caudal"},
            {"Cuenca": "Quebrada Amancaes", "Punto crítico": "Av. Sucre",
             "Nivel": nivel, "Tendencia": "estable"},
        ]
        import pandas as _pd
        df_c = _pd.DataFrame(cuencas)
        st.dataframe(df_c, use_container_width=True, hide_index=True)

    with right:
        st.markdown("#### 📋 Bitácora de incidentes")
        if "bitacora" not in st.session_state:
            st.session_state["bitacora"] = [
                {"Hora": now_iso, "Evento": f"Evaluación automática → {nivel}",
                 "Detalle": decision.reasons[0][:90]},
            ]
        for ev in st.session_state["bitacora"][:6]:
            st.markdown(
                f"`{ev['Hora']}` — **{ev['Evento']}**  \n"
                f"<span style='opacity:.75'>{ev['Detalle']}</span>",
                unsafe_allow_html=True,
            )
        nuevo = st.text_input("Registrar nueva entrada en la bitácora")
        if st.button("➕ Añadir a bitácora") and nuevo:
            st.session_state["bitacora"].insert(
                0, {"Hora": now_iso, "Evento": "Registro manual COE", "Detalle": nuevo}
            )
            st.rerun()

    st.divider()

    # ---------- Protocolos de activación por nivel ----------
    st.markdown("#### 📯 Protocolos de activación")
    proto = {
        "VERDE": ("#2e7d32", [
            "Monitoreo pasivo: Sentinel-1 cada 12 h; IMERG cada 6 h.",
            "Sin notificaciones externas.",
        ]),
        "AMARILLO": ("#f9a825", [
            "Monitoreo intensivo: Sentinel-1 cada 6 h + pronóstico horario.",
            "Pre-aviso por WhatsApp a brigadas y líderes locales.",
            "Verificar puntos de evacuación y rutas alternas.",
        ]),
        "ROJO": ("#c62828", [
            "Activación inmediata del COE (turno completo).",
            "Notificación WhatsApp/SMS a Defensa Civil, COER y municipios.",
            "Boletín PDF por hora; sirenas y mensajes a celulares si aplica.",
            "Cierre preventivo de vías bloqueadas listadas en el simulador.",
        ]),
    }
    color_p, pasos = proto[nivel]
    st.markdown(
        f'<div style="border-left:5px solid {color_p};padding:8px 14px;'
        f'background:rgba(127,127,127,.08);border-radius:8px">'
        f'<b style="color:{color_p}">Protocolo {nivel}</b>' +
        "".join(f"<div>• {p}</div>" for p in pasos) + "</div>",
        unsafe_allow_html=True,
    )

    # ---------- Boletín del evento (payload + descargas) ----------
    st.markdown("#### 📰 Boletín del evento")
    bl1, bl2, bl3 = st.columns(3)
    import json as _json
    payload = {
        "sistema": "HidroAlert-COE",
        "nivel": nivel,
        "zona": snapshot.aoi_name,
        "timestamp": result.timestamp,
        "hidrologia": hid,
        "impacto": result.impact.to_dict(),
        "razones": decision.reasons,
    }
    bl1.download_button(
        "⬇️ Descargar JSON", data=_json.dumps(payload, ensure_ascii=False, indent=2,
                                                default=str),
        file_name=f"boletin_{nivel.lower()}.json", mime="application/json",
        use_container_width=True,
    )
    msg = compose_alert_message(result, decision)
    bl2.download_button(
        "⬇️ Mensaje WhatsApp", data=msg, file_name="mensaje_alerta.txt",
        mime="text/plain", use_container_width=True,
    )
    if bl3.button("🧾 Generar boletín PDF", use_container_width=True):
        with st.spinner("Generando…"):
            paths = generate_alert_report(result, decision)
        ok = {k: Path(v).name for k, v in paths.items() if v}
        st.success(f"Generado: {', '.join(ok.values())}")

# ===========================================================================
# TAB 4 — DATOS & MÉTODO
# ===========================================================================
with tab_met:
    st.subheader("📚 Fuentes de datos utilizadas")
    if fuente:
        st.success(f"**Datos reales activos** para `{snapshot.aoi_name}` "
                   f"({snapshot.hand.shape[0]}×{snapshot.hand.shape[1]} celdas de 30 m)")
        m1, m2, m3 = st.columns(3)
        with m1:
            st.markdown(f"""
            #### 🛰️ Radar Sentinel-1
            *Colección:* `COPERNICUS/S1_GRD` (GEE)
            *Umbral Otsu automático* + máscara HAND ≤ 15 m.
            *Agua observada:* **{snapshot.observed_water_area_m2/1e4:.1f} ha**
            """)
        with m2:
            st.markdown("""
            #### ⛰️ HAND / DEM
            *Dataset:* `MERIT/Hydro/v1_0_1` — bandas `hnd` (HAND) y `elv` (elevación).
            La lámina por celda = desborde sobre bankfull − HAND local.
            """)
        with m3:
            n_b = len(snapshot.buildings["features"]) if snapshot.buildings else 0
            st.markdown(f"""
            #### 🏠 Exposición
            *Edificios:* **{n_b}** huellas (MS Buildings Perú / GEE)
            *Vías:* GRIP4 Central-South-America
            *Agricultura:* ESA WorldCover (clase 40)
            """)
    else:
        st.info("Modo demo: terreno sintético para probar sin credenciales.")

    st.divider()
    st.subheader("🧮 Modelo hidrológico")
    st.latex(r"""
        h_{cauce} = \alpha \cdot P \cdot C_{cuenca} + \beta \sqrt{\Delta Q} \\
        h_{celda} = \max(0,\; h_{cauce} - H_{bankfull} - HAND_{celda}) \\
        V = \sum h_{celda} \cdot A_{celda}
    """)
    st.markdown(f"""
    * **Capacidad de banco (bankfull):** {BANKFULL_DEPTH_M:.2f} m — la lluvia
      moderada queda contenida en el cauce; solo el excedente inunda la llanura.
    * **Coeficientes:** α = 0.35 · C = 25 · β = 0.70 (calibrables en
      `hydrology/simulation_engine.py`).
    * **Umbrales de profundidad:** edificio afectado ≥ 0.15 m · vía bloqueada ≥ 0.20 m.
    """)

# ===========================================================================
# TAB 4 — ACERCA DE
# ===========================================================================
with tab_acerca:
    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown(f"""
        ### 🌊 HidroAlert v{__version__}
        Sistema de **monitoreo, simulación y alerta temprana** de inundaciones,
        desbordes de ríos y fallas de quebrada para el workspace
        `jhons-workspace-amus9`.

        **Arquitectura**
        | Capa | Tecnología |
        |---|---|
        | Observación | Google Earth Engine (Sentinel-1, MERIT Hydro, IMERG) |
        | Exposición | MS Buildings Perú · GRIP4 · WorldCover |
        | Motor | NumPy + Shapely (modelo HAND-bankfull) |
        | Escorrentía | Concentración de agua sobre terreno (ruteo D8) |
        | Pronóstico | WeatherNext 3 (opcional) / Open-Meteo |
        | UI | Streamlit + Folium + Plotly |
        | Alertas | Twilio WhatsApp/SMS · Webhook COER · PDF |

        **Niveles de alerta**
        * 🟢 **VERDE** — sin amenaza detectada.
        * 🟡 **AMARILLO** — precaución: hidrología favorable a inundación.
        * 🔴 **ROJO** — evacuación inminente por desborde / falla de quebrada.
        """)
    with c2:
        st.markdown("### 🚀 Cómo usar")
        st.markdown("""
        1. **Elija el área** en la barra lateral (bbox WGS84).
        2. **Active datos reales** (toggle Earth Engine).
        3. **Simule** con escenarios o sliders finos.
        4. **Revise el pronóstico 48 h** para anticipar el nivel.
        5. **Notifique o genere el informe** al pasar a AMARILLO/ROJO.
        """)
