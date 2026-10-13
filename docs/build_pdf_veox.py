"""
build_pdf_veox.py — Genera el PDF del Formulario de Postulación CONCYTEC/
PROCIENCIA del proyecto VEOX-FLOOD, con validación automática de límites
de caracteres por campo.

Salida: hidroalert/docs/Formulario_POSTULACION_VEOX_PROCIENCIA.pdf
"""

from __future__ import annotations

import sys
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import XPos, YPos

sys.path.insert(0, str(Path(__file__).resolve().parent))

import form_veox as F

# Colores institucionales
AZUL = (21, 62, 110)
GRIS = (70, 80, 90)
VERDE = (46, 125, 50)
ROJO = (183, 28, 28)

# Fuente Unicode (DejaVu Sans incluida en matplotlib) — soporta —, ≥, ², ≈
_FONT_DIR = Path(__file__).resolve().parents[1] / ".venv" / "Lib" / "site-packages" / "matplotlib" / "mpl-data" / "fonts" / "ttf"
FONT_REG = str(_FONT_DIR / "DejaVuSans.ttf")
FONT_BOLD = str(_FONT_DIR / "DejaVuSans-Bold.ttf")
FONT_OBL = str(_FONT_DIR / "DejaVuSans-Oblique.ttf")


class FormPDF(FPDF):
    """FPDF con encabezado/pie de página institucional y fuentes Unicode."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.add_font("DejaVu", "", FONT_REG)
        self.add_font("DejaVu", "B", FONT_BOLD)
        self.add_font("DejaVu", "I", FONT_OBL)
        self.font_family = "DejaVu"

    def setf(self, style: str = "", size: float = 10):
        """Atajo: set_font DejaVu."""
        self.set_font("DejaVu", style, size)


def build() -> tuple[Path, list[str]]:
    """Construye el PDF y devuelve (ruta, lista de advertencias de límites)."""
    pdf = FormPDF()
    pdf.set_margins(18, 20, 18)
    pdf.set_auto_page_break(auto=True, margin=22)
    pdf.add_page()

    # -------------------------------------------------------------- portada
    pdf.set_fill_color(*AZUL)
    pdf.set_text_color(255, 255, 255)
    pdf.setf("B", 17)
    pdf.cell(0, 14, ("FORMULARIO DE POSTULACIÓN"), fill=True,
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.setf("", 10)
    pdf.cell(0, 10, ("Investigación Aplicada y Desarrollo Tecnológico — Modalidad Avanzada"),
             fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)
    pdf.set_text_color(*AZUL)
    pdf.setf("B", 12)
    pdf.multi_cell(0, 7, ("Proyecto VEOX-FLOOD\n" + F.TITULO))
    pdf.ln(2)
    pdf.setf("", 10)
    pdf.set_text_color(*GRIS)
    pdf.multi_cell(
        0, 5.5,
        (
            "Entidades: UTEC (solicitante) · VEOX S.A.C. (asociada) | "
            "Responsable técnico: MSc. Wilder Nina Choquehuayta (ORCID 0000-0002-6027-4973) | "
            "Ámbito: Piura y Tumbes | Presupuesto: S/. 500 000,00 | Duración: 24 meses"
        ),
    )
    pdf.ln(2)

    warn: list[str] = []

    def seccion(num: int, titulo: str) -> None:
        pdf.ln(2)
        pdf.set_fill_color(*AZUL)
        pdf.set_text_color(255, 255, 255)
        pdf.setf("B", 12)
        pdf.cell(0, 9, (f"  {num}. {titulo.upper()}"), fill=True,
                 new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(2)

    def campo(label: str, contenido: str, limite: int | None = None) -> None:
        if limite is not None and len(contenido) > limite:
            warn.append(f"[LÍMITE] '{label}': {len(contenido)} > {limite} caracteres")
        pdf.setf("B", 10)
        pdf.set_text_color(*AZUL)
        extra = f"  (máx. {limite} car.)" if limite else ""
        pdf.cell(0, 6, (f"{label}{extra}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.setf("", 9.5)
        pdf.set_text_color(30, 35, 40)
        pdf.multi_cell(0, 5.2, (contenido))
        pdf.ln(1.5)

    def bullets(items: list[str]) -> None:
        pdf.setf("", 9.5)
        pdf.set_text_color(30, 35, 40)
        for it in items:
            pdf.multi_cell(0, 5.2, (f"• {it}"))
            pdf.ln(0.8)
        pdf.ln(1)

    def tabla(filas: list[tuple[str, str, str, str, str]], headers: tuple[str, ...]) -> None:
        widths = [22, 52, 16, 16, 74]
        pdf.setf("B", 8.5)
        pdf.set_fill_color(225, 232, 240)
        pdf.set_text_color(*AZUL)
        for w, h in zip(widths, headers):
            pdf.cell(w, 6, (h), border=1, fill=True)
        pdf.ln()
        pdf.setf("", 8)
        pdf.set_text_color(30, 35, 40)
        for fila in filas:
            h = max(
                pdf.get_string_width((str(v))) / (w - 3) * 4.6 + 2.2
                for w, v in zip(widths, fila)
            )
            h = min(max(h, 6), 40)
            for w, v in zip(widths, fila):
                pdf.cell(w, h, (str(v)), border=1)
            pdf.ln(h)
        pdf.ln(2)

    # ===================================================== 1. DECLARACIÓN
    seccion(1, "Declaración Jurada e Indicaciones Básicas")
    campo("Declaración jurada", F.DECLARACION_JURADA)
    campo("Indicaciones básicas", "Compromisos generales del postulante:")
    bullets(F.INDICACIONES_BASICAS)

    # ===================================================== 2. INFO GENERAL
    seccion(2, "Información General")
    campo("Título del proyecto", F.TITULO, 250)
    campo("Resumen publicable", F.RESUMEN_PUBLICABLE, 2000)
    campo("Modalidad", F.MODALIDAD)

    # ===================================================== 3. PRIORIDADES
    seccion(3, "Prioridades del Concurso y Clasificación OCDE")
    campo("Prioridad temática", F.PRIORIDAD_CONCURSO)
    for k, v in F.CLASIFICACION_OCDE.items():
        campo(k, v)

    # ===================================================== 4. LUGAR
    seccion(4, "Lugar de Ejecución")
    campo("Lugar de ejecución principal", f"{F.LUGAR_PRINCIPAL['Departamento']} — {F.LUGAR_PRINCIPAL['Provincias']} — {F.LUGAR_PRINCIPAL['Distritos']}")
    campo("Justificación (Piura)", F.LUGAR_PRINCIPAL["Justificación"])
    campo("Lugar de ejecución adicional", f"{F.LUGAR_ADICIONAL['Departamento']} — {F.LUGAR_ADICIONAL['Provincias']} — {F.LUGAR_ADICIONAL['Distritos']}")
    campo("Justificación (Tumbes)", F.LUGAR_ADICIONAL["Justificación"])

    # ===================================================== 5. PALABRAS CLAVE
    seccion(5, "Palabras Clave (14 términos)")
    campo("Palabras clave", "; ".join(F.PALABRAS_CLAVE))

    # ===================================================== 6. ÉTICA
    seccion(6, "Aspectos Éticos, Ambientales y Normativos")
    for k, v in F.ASPECTOS_ETICOS.items():
        campo(k.capitalize(), v)

    # ===================================================== 7. ENTIDADES
    seccion(7, "Datos de las Entidades Participantes")
    for k, v in F.ENTIDAD_SOLICITANTE.items():
        campo(f"Entidad solicitante — {k}", v)
    campo("Trayectoria de la entidad solicitante (UTEC)", F.TRAYECTORIA_UTEC, 5000)
    for k, v in F.ENTIDAD_ASOCIADA.items():
        campo(f"Entidad asociada — {k}", v)
    campo("Participación de la entidad asociada (VEOX S.A.C.)", F.PARTICIPACION_VEOX, 1000)

    # ===================================================== 8. EQUIPO
    seccion(8, "Conformación del Equipo Humano")
    for m in F.EQUIPO_HUMANO:
        campo(f"{m['Rol']}", f"{m['Perfil']}\nFunciones: {m['Funciones']}\nDedicación: {m['Dedicación']}")

    # ===================================================== 9. PROPUESTA
    seccion(9, "Propuesta Técnica y Científica")
    campo("Resumen ampliado de la propuesta", F.RESUMEN_AMPLIADO, 5000)
    campo("Planteamiento del problema", F.PLANTEAMIENTO_PROBLEMA, 5000)
    campo("Justificación socioeconómica y tecnológica", F.JUSTIFICACION, 4000)
    campo("Novedad e innovación", F.NOVEDAD_INNOVACION, 2000)
    campo("Objetivo general", F.OBJETIVO_GENERAL)
    campo("Objetivos específicos", "\n\n".join(
        f"({chr(10).join([oe])})" if False else oe for oe in F.OBJETIVOS_ESPECIFICOS
    ))
    campo("Estado del arte", F.ESTADO_DEL_ARTE, 5000)
    campo("Nivel de madurez tecnológica — Ingreso", f"{F.TRL_INGRESO}\n{F.TRL_INGRESO_FUNDAMENTO}")
    campo("Nivel de madurez tecnológica — Salida", f"{F.TRL_SALIDA}\n{F.TRL_SALIDA_FUNDAMENTO}")
    campo("Metodología en extenso (por objetivos específicos)", F.METODOLOGIA, 5000)

    # ===================================================== 10. VIABILIDAD
    seccion(10, "Viabilidad Operativa, Cronograma y Riesgos")
    campo("Cronograma (24 meses)", "Plan de ejecución por periodos:")
    tabla([(p, a, r, "", "") for p, a, r in F.CRONOGRAMA],
          ("Periodo", "Actividad", "Responsable", "Hitos/KPI", "Evidencia esperada"))
    campo("Matriz de riesgos y mitigación",
          "Riesgos identificados con probabilidad, impacto y plan de mitigación:")
    tabla(F.RIESGOS, ("Tipo", "Riesgo", "Prob.", "Impacto", "Mitigación"))

    # ===================================================== 11. RESULTADOS
    seccion(11, "Resultados Esperados")
    campo("Resultados obligatorios PROCIENCIA", "Cumplimiento estructural de la convocatoria:")
    bullets(F.RESULTADOS_OBLIGATORIOS)
    campo("Resultados tecnológicos y de transferencia", None if False else "Productos verificables del sistema:", ) if False else campo("Resultados tecnológicos y de transferencia", "Productos verificables del sistema:")
    bullets(F.RESULTADOS_TECNOLOGICOS)
    campo("Indicadores de resultados", "Tabla de indicadores con metas y plazos:")
    tabla([(i, m, "", p, "") for i, m, p in F.INDICADORES_RESULTADOS],
          ("Indicador", "Meta", "Medio de verificación", "Plazo", "Estado"))

    # ===================================================== 12. PGD
    seccion(12, "Plan de Gestión de Datos de Investigación (FAIR / ALICIA 2.0.1)")
    for k, v in F.PGD.items():
        campo(k, v)

    # ===================================================== 13. PRESUPUESTO
    seccion(13, "Cuadro Resumen Presupuestal")
    campo("Presupuesto por rubros", "Detalle en soles (S/.):")
    pdf.setf("B", 9)
    pdf.set_fill_color(225, 232, 240)
    pdf.set_text_color(*AZUL)
    pdf.cell(20, 7, ("Rubro"), border=1, fill=True)
    pdf.cell(130, 7, ("Descripción"), border=1, fill=True)
    pdf.cell(35, 7, ("Monto (S/.)"), border=1, fill=True, align="R")
    pdf.ln()
    pdf.setf("", 9)
    pdf.set_text_color(30, 35, 40)
    for rubro, desc, monto in F.PRESUPUESTO:
        h = 6 if pdf.get_string_width((desc)) < 125 else 10
        pdf.cell(20, h, (rubro), border=1)
        pdf.cell(130, h, (desc), border=1)
        pdf.cell(35, h, (monto), border=1, align="R")
        pdf.ln(h)
    pdf.setf("B", 10)
    pdf.set_fill_color(*VERDE)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(150, 8, ("PRESUPUESTO TOTAL"), border=1, fill=True)
    pdf.cell(35, 8, ("500 000,00"), border=1, fill=True, align="R")
    pdf.ln(8)
    pdf.set_text_color(*GRIS)
    pdf.setf("", 9)
    pdf.cell(0, 6, (F.PRESUPUESTO_TOTAL))

    # -------------------------------------------------------------- salida
    out = Path(__file__).resolve().parent / "Formulario_POSTULACION_VEOX_PROCIENCIA.pdf"
    pdf.output(str(out))
    return out, warn


if __name__ == "__main__":
    path, warnings = build()
    print(f"PDF generado: {path}")
    print(f"Tamaño: {path.stat().st_size / 1024:.0f} KB")
    if warnings:
        print("\nADVERTENCIAS DE LÍMITES:")
        for w in warnings:
            print(" ", w)
    else:
        print("Todos los campos cumplen sus límites de caracteres.")
