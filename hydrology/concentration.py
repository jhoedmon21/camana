"""
concentration.py — Concentración de agua sobre el terreno (escorrentía superficial).

Complementa el modelo de desborde de cauce (HAND + bankfull) con la
hidrología de ladera: la lluvia genera escorrentía local que fluye celda a
celda hacia su vecino de máxima pendiente (ruteo D8 sobre el DEM) y se
CONCENTRA en las depresiones del terreno (pozas, terrazas bajas, zonas
planas sin salida gravitacional), desde donde no puede drenar.

    lluvia → escorrentía (coeficiente) → ruteo D8 celda a celda → pozas

Reglas del ruteo:
    * Depresión (sin vecino más bajo): el agua que llega SE QUEDA ⇒ poza.
    * Red de drenaje (HAND ≤ DRAINAGE_HAND_M, el cauce): ABSORBE el flujo
      que la alcanza — el desborde/transporte del cauce ya lo modela
      `simulation_engine.simulate_flood`, así no se cuenta dos veces.
    * Borde del dominio: el agua SALE del área de análisis.
    * En tránsito: el agua se infiltra gradualmente (pérdida por paso).

La lámina resultante se integra a la simulación cuando
`simulate_flood(include_overland=True)` y está INCORPORADA POR DEFECTO en
la línea de tiempo del pronóstico (`timeline.build_alert_timeline`), de
modo que la predicción horaria de lluvias también predice dónde y cuánto
agua se concentra sobre el terreno.
"""

from __future__ import annotations

import numpy as np

from hidroalert.models import AreaSnapshot

# --- Parámetros de calibración (modelo conceptual, consistentes con el estilo
# de simulation_engine: valores explícitos y documentados) ---
# Fracción de la lluvia que no se infiltra en el punto de caída y fluye
# sobre el terreno (SCS-ish para suelos de valle costero)
OVERLAND_RUNOFF_COEFF = 0.35
# Fracción del agua de una celda que pasa a su receptor D8 en cada paso
TRANSFER_FRACTION = 0.90
# Infiltración en tránsito: fracción que se pierde por paso de ruteo
IN_TRANSIT_LOSS = 0.06
# Pasos de ruteo por hora simulada (~1 celda/paso ⇒ 12 pasos ≈ 1.2 km/h
# a resolución de 100 m: velocidad plausible de escorrentía laminar)
ROUTING_STEPS = 12
# Celdas con HAND ≤ este valor (m) forman la red de drenaje: absorben la
# escorrentía que las alcanza (el cauce la transporta / desborda)
DRAINAGE_HAND_M = 1.0

# Vecindario D8 (drow, dcol); el orden resuelve empates de pendiente
_OFFSETS = (
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1), (0, 1),
    (1, -1), (1, 0), (1, 1),
)

# Marcas de receptor en el ráster aplanado
_SINK = -2      # depresión interna: el agua que llega se queda (poza)
_OUTFLOW = -1   # borde del dominio: el agua sale del área de análisis


def d8_receivers(dem: np.ndarray) -> np.ndarray:
    """
    Receptor D8 (vecino de máxima caída) por celda, como índices planos.

    Reglas:
        * Receptor = vecino con mayor caída positiva (dem[celda] − dem[vecino]);
          empates → el primer offset del orden `_OFFSETS`.
        * Sin vecino más bajo → `_SINK` (depresión: el agua se acumula).
        * Vecino fuera de la matriz (borde, relleno con −inf ⇒ caída
          infinita) → `_OUTFLOW` (el agua abandona el dominio).
        * Celdas sin dato (NaN → +inf) no reciben flujo de nadie.

    Returns:
        ndarray int64 de tamaño nrows*ncols con el índice plano del
        receptor, o _SINK / _OUTFLOW.
    """
    nrows, ncols = dem.shape
    d = np.where(np.isfinite(dem), dem, np.inf)

    recv = np.full((nrows, ncols), _SINK, dtype=np.int64)
    best_drop = np.zeros((nrows, ncols), dtype=np.float64)
    rows = np.arange(nrows)[:, None]
    cols = np.arange(ncols)[None, :]

    for dr, dc in _OFFSETS:
        # Elevación del vecino; −inf si cae fuera del dominio (borde abierto)
        nb = np.full((nrows, ncols), -np.inf)
        r0, r1 = max(0, -dr), nrows - max(0, dr)
        c0, c1 = max(0, -dc), ncols - max(0, dc)
        nb[r0:r1, c0:c1] = d[r0 + dr:r1 + dr, c0 + dc:c1 + dc]

        # NaN (inf − inf) solo cuando celda y vecino están ambas sin dato DEM:
        # la comparación NaN > best_drop es False (no gana), pero silenciamos
        # el warning de numpy para no contaminar los logs del servicio.
        with np.errstate(invalid="ignore"):
            drop = d - nb
        better = drop > best_drop
        best_drop = np.where(better, drop, best_drop)

        # Índice plano del vecino; _OUTFLOW si está fuera de la matriz
        inside = (
            ((rows + dr) >= 0) & ((rows + dr) < nrows)
            & ((cols + dc) >= 0) & ((cols + dc) < ncols)
        )
        nflat = np.where(inside, (rows + dr) * ncols + (cols + dc), _OUTFLOW)
        recv = np.where(better, nflat, recv)

    return recv.ravel()


def overland_concentration(
    snapshot: AreaSnapshot,
    precipitation_mm_h: float,
    duration_h: float = 1.0,
) -> tuple[np.ndarray, dict]:
    """
    Lámina de agua concentrada sobre el terreno (m) para una lluvia dada.

    Modelo: cada celda válida produce escorrentía local (lluvia ×
    OVERLAND_RUNOFF_COEFF); el agua se traslada a su receptor D8 durante
    ROUTING_STEPS pasos, infiltrándose en el trayecto. Las depresiones
    retienen lo que llega (pozas), la red de drenaje absorbe el flujo y el
    borde del dominio lo deja salir.

    Args:
        snapshot:            contexto del área (Módulo 1); usa DEM y HAND.
        precipitation_mm_h:  intensidad de lluvia (mm/h).
        duration_h:          duración del pulso (h); 1 h por defecto
                             (la línea de tiempo simula hora a hora).

    Returns:
        (depth_m 2D, stats) donde stats = {volume_m3, area_m2, max_depth_m}.
        El volumen/área usan el mismo corte de 1 cm que el motor principal,
        de modo que `overland_volume_m3` es la porción que realmente aporta
        a la lámina de inundación (las películas < 1 cm no cuentan).
    """
    dem = snapshot.dem
    nrows, ncols = dem.shape
    depth = np.zeros((nrows, ncols), dtype=np.float64)
    if precipitation_mm_h <= 0 or not np.isfinite(dem).any():
        return depth, _stats(depth, snapshot)

    valid = np.isfinite(dem) & np.isfinite(snapshot.hand)
    drainage = valid & (np.nan_to_num(snapshot.hand, nan=np.inf) <= DRAINAGE_HAND_M)

    # Receptores D8 (cacheados en el snapshot: el terreno no cambia entre horas)
    recv = getattr(snapshot, "_d8_receivers", None)
    if recv is None or recv.shape != (nrows * ncols,):
        recv = d8_receivers(dem)
        try:
            snapshot._d8_receivers = recv  # dataclass sin slots: admite caché
        except AttributeError:  # pragma: no cover - defensivo
            pass

    # Lluvia del pulso → escorrentía local (lámina m por celda)
    rain_m = precipitation_mm_h * duration_h / 1000.0
    w = np.where(valid.ravel(), rain_m * OVERLAND_RUNOFF_COEFF, 0.0)
    drainage_flat = drainage.ravel()

    # Pueden enviar agua: celdas válidas fuera del drenaje que no son poza
    sendable = valid.ravel() & ~drainage_flat & (recv != _SINK)

    for _ in range(ROUTING_STEPS):
        active = sendable & (w > 1e-9)
        if not active.any():
            break
        send = np.where(active, w * TRANSFER_FRACTION, 0.0)
        w = w - send
        # El caudal que llega a un vecino dentro del dominio se suma;
        # lo enviado al borde (_OUTFLOW) sale y no vuelve a contarse
        to_nb = active & (recv >= 0)
        inflow = np.bincount(
            recv[to_nb], weights=send[to_nb], minlength=w.size
        ).astype(np.float64)
        w = w + inflow
        w *= 1.0 - IN_TRANSIT_LOSS       # infiltración en tránsito
        w[drainage_flat] = 0.0           # absorción por la red de drenaje

    depth = w.reshape(nrows, ncols)
    return depth, _stats(depth, snapshot)


def _stats(depth: np.ndarray, snapshot: AreaSnapshot) -> dict:
    """Resumen serializable de la lámina concentrada (corte 1 cm, como el motor)."""
    mask = depth > 0.01
    return {
        "volume_m3": float(depth[mask].sum() * snapshot.cell_area_m2),
        "area_m2": float(mask.sum() * snapshot.cell_area_m2),
        "max_depth_m": float(depth.max()) if depth.size else 0.0,
    }
