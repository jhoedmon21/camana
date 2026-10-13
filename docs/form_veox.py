"""
form_veox.py — Formulario de Postulación CONCYTEC/PROCIENCIA (contenido).

Proyecto VEOX: Sistema Inteligente Multimodal de Monitoreo, Detección Temprana
y Predicción de Inundaciones Dinámicas mediante Redes IoT, Teledetección
Satelital SAR e Inteligencia Artificial.

Cada campo es una tupla (etiqueta, contenido, límite_de_caracteres). El
generador de PDF (build_pdf_veox.py) valida automáticamente que ningún
campo exceda su límite oficial.

El contenido describe la arquitectura REAL implementada en este repositorio
(hidroalert/): ingesta GEE Sentinel-1 + MERIT Hydro (HAND/upa/elv), Google
Open Buildings V3 / MS Buildings, GRIP4, ESA WorldCover, motor hidrológico
HAND-bankfull con propagación horaria, FastAPI + CesiumJS/deck.gl, IMERG,
Open-Meteo/WeatherNext, alertas Twilio/Webhook COER y pruebas automatizadas.
"""

# ===========================================================================
# 1. DECLARACIÓN JURADA E INDICACIONES BÁSICAS
# ===========================================================================
DECLARACION_JURADA = (
    "Los abajo firmantes declaramos bajo juramento que la información contenida en el "
    "presente Formulario de Postulación es veraz, completa y verificable; que las "
    "entidades participantes cuentan con la capacidad y disposición para ejecutar el "
    "proyecto en los plazos y condiciones propuestos; que no existe conflicto de "
    "intereses con el personal evaluador de PROCIENCIA; que los resultados de la "
    "investigación se gestionarán conforme al Código de Integridad Científica de "
    "CONCYTEC (Resolución N.° 032-2019-CONCYTEC-CD) y a la Guía ALICIA 2.0.1 para la "
    "Gestión de Datos de Investigación; y que nos comprometemos a cumplir la normativa "
    "nacional aplicable, incluida la Ley N.° 30215 (inversión en I+D con beneficios "
    "tributarios), la Ley N.° 29578 y las disposiciones del Reglamento del concurso. "
    "Asimismo, declaramos que la propuesta no duplica proyectos financiados con fondos "
    "públicos y que los datos satelitales e hidrológicos empleados provienen de fuentes "
    "abiertas (Copernicus, NASA GPM, MERIT Hydro, ESA WorldCover) de libre acceso."
)

INDICACIONES_BASICAS = [
    "El presente formulario corresponde a la Modalidad Avanzada de Investigación Aplicada y Desarrollo Tecnológico.",
    "El presupuesto total solicitado asciende a S/. 500 000,00 (quinientos mil con 00/100 soles), cofinanciado por las entidades participantes.",
    "La ejecución es de 24 meses, alineada a dos temporadas de lluvias (diciembre–marzo) para la validación operativa del prototipo.",
    "Toda la información técnica declarada es auditable: el sistema VEOX-FLOOD opera ya en modo prototipo (TRL 3/4) con datos abiertos y su evidencia se adjunta como anexo.",
    "Los datos personales del equipo han sido autorizados para su tratamiento según la Ley N.° 29733 (Protección de Datos Personales).",
]

# ===========================================================================
# 2. INFORMACIÓN GENERAL
# ===========================================================================
TITULO = (
    "Sistema Inteligente Multimodal de Monitoreo, Detección Temprana y Predicción "
    "de Inundaciones Dinámicas mediante Redes IoT, Teledetección Satelital SAR e "
    "Inteligencia Artificial (VEOX-FLOOD)"
)

RESUMEN_PUBLICABLE = (
    "Las inundaciones asociadas al Fenómeno El Niño (FEN) constituyen el peligro "
    "natural de mayor impacto socioeconómico en el norte del Perú: solo el FEN "
    "2017 dejó 162 fallecidos y pérdidas por S/. 9 162 millones en Piura. VEOX-FLOOD "
    "propone un sistema inteligente multimodal que integra (i) una red de nodos IoT "
    "autónomos con sensores radar/ultrasonido de nivel de río y pluviómetros de "
    "cubeta, con transmisión híbrida LoRaWAN (915 MHz)/GPRS-4G; (ii) teledetección "
    "satelital SAR Copernicus Sentinel-1 (banda C, 5.405 GHz, VV/VH) insensible a "
    "la cobertura nubosa, con umbralización de Otsu restringida por el índice "
    "topográfico HAND (Height Above Nearest Drainage, MERIT Hydro) para el mapeo "
    "de agua libre; y (iii) modelos de aprendizaje profundo: redes LSTM con "
    "mecanismo de atención para predicción de nivel/caudal a horizontes de 24–48 h "
    "(métricas objetivo R² ≥ 0.85, RMSE ≤ 0.15 m) y redes convolucionales U-Net "
    "para segmentación espacial de áreas inundables (F1-Score ≥ 0.90, IoU ≥ 0.82). "
    "Los resultados se integran en la plataforma cloud VEOX-FLOOD (FastAPI, "
    "PostgreSQL/PostGIS, CesiumJS/deck.gl), que expone dashboards 3D de comando, "
    "una API pública documentada y alertas masivas SMS/WhatsApp/correo mediante "
    "protocolos institucionales (COER, Defensa Civil). El prototipo ya opera con "
    "las 11 provincias de Piura y Tumbes en modo TRL 3/4; el proyecto elevará la "
    "madurez a TRL 6/7 validando el sistema en entorno real durante dos temporadas "
    "de lluvias en las cuencas del Río Piura (Catacaos, Tambogrande, Sechura) y del "
    "Río Tumbes (Zarumilla), con una red piloto de 8 nodos IoT y métricas de "
    "operación certificadas. El producto final es un sistema de alerta temprana "
    "combinada (in situ + satelital + IA) replicable en otras cuencas del país, "
    "generando capacidades permanentes en UTEC y VEOX S.A.C., y evidencia científica "
    "publicable en revistas indexadas de hidrología computacional y teledetección."
)

MODALIDAD = "Avanzada (Investigación Aplicada y Desarrollo Tecnológico)"

# ===========================================================================
# 3. PRIORIDADES DEL CONCURSO Y CLASIFICACIÓN OCDE
# ===========================================================================
PRIORIDAD_CONCURSO = (
    "Monitoreo de Peligros, Alerta Temprana y Gestión del Riesgo de Desastres ante "
    "el Fenómeno El Niño (FEN) — eventos hidrometeorológicos extremos en la costa "
    "norte del Perú."
)

CLASIFICACION_OCDE = {
    "Área (nivel 1)": "Ingeniería y Tecnología",
    "Disciplina (nivel 2)": "Ciencias de la Computación e Inteligencia Artificial",
    "Subdisciplina (nivel 3)": "1.6.16 — Inteligencia Artificial; 1.4.10 — Hidrología Computacional (interdisciplina)",
    "Interdisciplinas": "Teledetección (1.5.02), Sistemas embebidos e IoT (1.6.27), Sistemas de información geográfica (1.5.15)",
}

# ===========================================================================
# 4. LUGAR DE EJECUCIÓN
# ===========================================================================
LUGAR_PRINCIPAL = {
    "Departamento": "Piura",
    "Provincias": "Piura, Sechura",
    "Distritos": "Piura (Catacaos, Cura Mori, El Tallán), Tambogrande, Sechura (Vice, Rinconada Llícuar)",
    "Justificación": (
        "Cuenca baja del Río Piura (37 400 km² hasta la desembocadura): en el FEN 2017 "
        "el distrito de Catacaos registró inundaciones urbanas >1.5 m y 23 000 damnificados. "
        "La escala regional del análisis satelital (100 m) y la red IoT se concentran en "
        "los puentes Piura–Catacaos y Tambogrande (control hidrológico principal)."
    ),
}

LUGAR_ADICIONAL = {
    "Departamento": "Tumbes",
    "Provincias": "Tumbes, Zarumilla",
    "Distritos": "Tumbes, San Jacinto, Corrales, Pampas de Hospital",
    "Justificación": (
        "Cuenca transfronteriza del Río Tumbes (5 357 km² de área upstream medida en "
        "MERIT Hydro): el FEN 2017 rompió el dique de Zarumilla. La réplica en Tumbes "
        "demuestra la transferibilidad del sistema en una segunda cuenca con régimen "
        "hidrológico distinto (río permanente de origen ecuatoriano)."
    ),
}

# ===========================================================================
# 5. PALABRAS CLAVE (mínimo 10)
# ===========================================================================
PALABRAS_CLAVE = [
    "Alerta temprana de inundaciones",
    "Fenómeno El Niño (FEN)",
    "Teledetección SAR (Sentinel-1)",
    "Umbralización de Otsu",
    "Índice HAND (Height Above Nearest Drainage)",
    "Internet de las Cosas (IoT) hidrológico",
    "LoRaWAN 915 MHz",
    "Redes LSTM con atención",
    "Segmentación U-Net",
    "Predicción de nivel de río (24–48 h)",
    "Hidrología computacional",
    "Gestión del riesgo de desastres (GRD)",
    "GEOINT / Sistemas de información geográfica",
    "Infraestructura de datos espaciales",
]

# ===========================================================================
# 6. ASPECTOS ÉTICOS, AMBIENTALES Y NORMATIVOS
# ===========================================================================
ASPECTOS_ETICOS = {
    "Integridad científica": (
        "Cumplimiento del Código de Integridad Científica de CONCYTEC: registro previo "
        "de datos y código en repositorio institucional (Zenodo/UTEC, DOI asignado), "
        "revisión por pares interna, y declaración de contribuciones tipo CRediT del "
        "equipo. Los modelos de IA se documentarán con fichas de datos (datasheets) y "
        "de modelo (model cards) para trazabilidad de decisiones de alerta."
    ),
    "Uso de datos personales": (
        "La plataforma gestiona únicamente datos operativos (niveles de río, lluvia, "
        "geometrías de inundación). El servicio de alertas masivas usa números de "
        "contacto provistos voluntariamente por los municipios y Defensa Civil bajo "
        "convenio, cumpliendo la Ley N.° 29733; no se procesan datos biométricos ni "
        "de terceros no autorizados."
    ),
    "Áreas Naturales Protegidas (ANP)": (
        "El ámbito incluye la zona de amortiguamiento del Santuario Nacional Manglares "
        "de San Pedro de Vice (Sechura). No se instalarán nodos dentro del ANP; las "
        "estaciones se ubicarán en infraestructura pública municipal existente. El "
        "mapeo satelital es pasivo y no requiere intervención en el hábitat."
    ),
    "Patrimonio arqueológico": (
        "Antes de la instalación de cada nodo se solicitará el informe de caracterización "
        "de riesgo arqueológico (CIRA) ante el Ministerio de Cultura, conforme a la Ley "
        "N.° 28296; se mantendrá distancia mínima de 50 m de sitios catalogados."
    ),
    "Impacto ambiental": (
        "Categoría de menor impacto: nodos alimentados por panel solar (10 W) con "
        "batería LiFePO₄ sellada, sin obra civil mayor (anclajes en puentes existentes). "
        "Al cierre del proyecto se aplicará un plan de gestión de residuos electrónicos "
        "con el socio industrial VEOX S.A.C."
    ),
    "Normativa sectorial": (
        "Coordinación con la Autoridad Nacional del Agua (ANA) — Autoridad Administrativa "
        "del Agua II Piura y I Tumbes — para el uso de información hidrológica oficial y "
        "compatibilidad con el Sistema Nacional de Información de Recursos Hídricos; "
        "aplicación de la Ley N.° 29664 (SINAGERD) y su Reglamento para el componente "
        "de alerta temprana comunitaria."
    ),
}

# ===========================================================================
# 7. DATOS DE LAS ENTIDADES
# ===========================================================================
ENTIDAD_SOLICITANTE = {
    "Razón social": "Universidad de Ingeniería y Tecnología (UTEC)",
    "RUC": "20486388224",
    "Naturaleza": "Universidad privada licenciada por SUNEDU, con reconocida producción "
                  "científica en ingeniería, ciencia de datos y energía (Scimago "
                  "Institutions Rankings: 1.er lugar en investigación per cápita).",
}

TRAYECTORIA_UTEC = (
    "UTEC es una universidad de investigación licenciada por SUNEDU cuyo modelo se "
    "sustenta en la generación de ciencia de frontera y traducción tecnológica. En "
    "Scimago Institutions Rankings figura consistentemente como la institución "
    "peruana con mayor producción científica per cápita, con publicaciones en Q1 en "
    "revistas de energía, materiales, hidrología y aprendizaje automático. Sus "
    "laboratorios de Sistemas Ciberfísicos, Ciencia de Datos y Fluidos cuentan con "
    "infraestructura para el desarrollo de nodos IoT (bancas de prototipado "
    "electrónico, cámaras anecoicas para pruebas RF en 915 MHz, estanques "
    "hidrodinámicos) y capacidad de cómputo (clusters GPU NVIDIA) para el "
    "entrenamiento de modelos de aprendizaje profundo. UTEC ha ejecutado proyectos "
    "financiados por PROCIENCIA (Proyectos de Investigación Aplicada, Proyectos de "
    "Ingeniería Aplicada para Entidades Reguladoras) y por fondos concursables "
    "internacionales (Wellcome Trust, Royal Academy of Engineering), cumpliendo "
    "deberes de reporte técnico y financiero sin observaciones. En el ámbito de "
    "riesgo de desastres, grupos de investigación de UTEC han trabajado en "
    "modelamiento de inundaciones urbanas con SIG y teledetección, monitoreo de "
    "quality of water con sensores de bajo costo, y geointeligencia aplicada. La "
    "Dirección de Investigación e Innovación (DIDI) provee gestión de proyectos, "
    "auditoría científica y articulación con las oficinas de Transferencia "
    "Tecnológica y de Responsabilidad Social, que facilitan el vínculo con "
    "municipios de Piura y la Autoridad Nacional del Agua. Para VEOX-FLOOD, UTEC "
    "aporta: (i) liderazgo científico en el diseño de los modelos LSTM-attention y "
    "U-Net; (ii) validación estadística y publicación en revistas indexadas; "
    "(iii) formación de capital humano (2 tesistas de maestría en Ciencia de Datos "
    "e Ingeniería); y (iv) gobernanza de datos bajo estándares FAIR. El sistema "
    "presentado en esta propuesta ya cuenta con un prototipo funcional desarrollado "
    "por el equipo (motor de ingesta Google Earth Engine Sentinel-1 + HAND, motor "
    "hidrológico de propagación, dashboard 3D y API), que se someterá a mejora, "
    "integración con los nodos IoT y validación de campo, elevando la madurez del "
    "TRL 3/4 al TRL 6/7 durante las temporadas de lluvias 2026–2028."
)

ENTIDAD_ASOCIADA = {
    "Razón social": "VEOX S.A.C.",
    "RUC": "20602091946",
    "Naturaleza": "Empresa peruana de tecnología (socio tecnológico industrial), "
                  "responsable del desarrollo de producto, la plataforma cloud y la "
                  "sostenibilidad comercial del sistema VEOX-FLOOD / SAMPLING.AI.",
}

PARTICIPACION_VEOX = (
    "VEOX S.A.C. participa como socio tecnológico industrial y co-ejecutora: "
    "(i) diseño industrial y manufactura de los 8 nodos IoT (carcaza IP67, "
    "electrónica LoRaWAN/4G, energía solar); (ii) desarrollo y operación 24/7 de la "
    "plataforma cloud VEOX-FLOOD/SAMPLING.AI (FastAPI, PostgreSQL/PostGIS, "
    "dashboards CesiumJS, API pública, alertas Twilio SMS/WhatsApp); (iii) "
    "despliegue de campo con cuadrillas técnicas en Piura y Tumbes; (iv) "
    "articulación comercial post-proyecto vía licenciamiento a municipalidades y "
    "autoridades del agua; y (v) cofinanciamiento en especie (ingeniería, cloud y "
    "equipo de prueba). VEOX será titular de los derechos patrimoniales de la marca "
    "VEOX-FLOOD según el acuerdo de consorcio, garantizando la ruta de mercado."
)

# ===========================================================================
# 8. CONFORMACIÓN DEL EQUIPO HUMANO
# ===========================================================================
EQUIPO_HUMANO = [
    {
        "Rol": "Investigador Principal (IP)",
        "Perfil": "MSc. Wilder Nina Choquehuayta (ORCID 0000-0002-6027-4973)",
        "Funciones": (
            "Liderazgo científico y técnico; diseño del esquema de fusión IoT+SAR+IA; "
            "supervisión de la validación en campo; correspondencia con PROCIENCIA; "
            "publicación de resultados."
        ),
        "Dedicación": "36 h/semana",
    },
    {
        "Rol": "Co-Investigador 1 — Hidrología computacional",
        "Perfil": "PhD en Ingeniería Civil / Recursos Hídricos (UTEC)",
        "Funciones": (
            "Calibración del modelo HAND-bankfull; verificación hidráulica con perfiles "
            "del ANA; diseño experimental de las campañas de aforo."
        ),
        "Dedicación": "20 h/semana",
    },
    {
        "Rol": "Co-Investigador 2 — Teledetección SAR / SIG",
        "Perfil": "PhD en Geociencias / Teledetección (UTEC)",
        "Funciones": (
            "Pipeline Google Earth Engine Sentinel-1 (Otsu+HAND); validación de máscaras "
            "de agua con ortofotos; análisis multitemporal del FEN."
        ),
        "Dedicación": "20 h/semana",
    },
    {
        "Rol": "Co-Investigador 3 — Aprendizaje automático",
        "Perfil": "PhD en Ciencia de la Computación (UTEC)",
        "Funciones": (
            "Arquitectura LSTM-attention y U-Net; régimen de experimentos (MLOps); "
            "evaluación R²/RMSE/F1/IoU y explicabilidad."
        ),
        "Dedicación": "20 h/semana",
    },
    {
        "Rol": "Gestor Tecnológico (socio)",
        "Perfil": "Ing. industrial — VEOX S.A.C.",
        "Funciones": (
            "Gestión de producto y TRL; plan de negocio; manufactura de nodos; enlace "
            "con municipios y COER; gestión de propiedad intelectual."
        ),
        "Dedicación": "20 h/semana",
    },
    {
        "Rol": "Tesista 1 (Maestría en Ciencia de Datos, UTEC)",
        "Perfil": "Ing. de sistemas / estadístico",
        "Funciones": (
            "Tesis: 'Predicción de nivel de río con LSTM-attention fusionando telemetría "
            "IoT y precipitación IMERG en la cuenca del Río Piura'."
        ),
        "Dedicación": "30 h/semana",
    },
    {
        "Rol": "Tesista 2 (Maestría en Ingeniería, UTEC)",
        "Perfil": "Ing. electrónica / geoespacial",
        "Funciones": (
            "Tesis: 'Segmentación de agua libre con U-Net sobre Sentinel-1 y evaluación "
            "fusión con HAND en cuencas del norte del Perú'."
        ),
        "Dedicación": "30 h/semana",
    },
    {
        "Rol": "Técnico de campo (VEOX)",
        "Perfil": "Técnico en electrónica y telecomunicaciones",
        "Funciones": "Instalación, mantenimiento y calibración de los 8 nodos IoT; logística de campañas.",
        "Dedicación": "Por campañas (8 campañas × 10 días)",
    },
]

# ===========================================================================
# 9. PROPUESTA TÉCNICA Y CIENTÍFICA
# ===========================================================================
RESUMEN_AMPLIADO = (
    "VEOX-FLOOD es un sistema ciberfísico de alerta temprana de inundaciones que "
    "integra de forma inédita en el Perú tres fuentes de información complementarias: "
    "(1) telemetría in situ mediante una red de 8 nodos IoT autónomos (sensor radar "
    "de nivel 80 GHz y/o ultrasonido 42 kHz, pluviómetro de cubeta basculante 0.2 mm, "
    "GPS y batería solar LiFePO₄) con comunicación híbrida LoRaWAN 915 MHz en zonas "
    "sin cobertura celular y conmutación automática a GPRS/4G donde existe; (2) "
    "teledetección satelital radar Copernicus Sentinel-1 GRD (banda C, 5.405 GHz, "
    "polarizaciones VV/VH, resolución 10 m, revisita 6–12 días) procesada en Google "
    "Earth Engine con umbralización automática de Otsu sobre la banda VH y filtrado "
    "topográfico HAND ≤ 15 m (MERIT Hydro), lo que reduce los falsos positivos por "
    "sombra radar; y (3) precipitación estimada por satélite IMERG (NASA GPM, 30 min, "
    "0.1°) y pronóstico horario (Open-Meteo/ECMWF), con arquitectura preparada para "
    "incorporar WeatherNext de Google. El núcleo predictivo combina dos modelos de "
    "aprendizaje profundo: (a) una red LSTM con mecanismo de atención que fusiona "
    "las series temporales de nivel (10 min), lluvia (30 min) y variables atmosféricas "
    "para predecir el nivel del río a 24 y 48 h (métricas objetivo R² ≥ 0.85, RMSE "
    "≤ 0.15 m, NSE ≥ 0.80); y (b) una red U-Net (encoder-decoder con skip connections) "
    "que segmenta la lámina de agua sobre mosaicos Sentinel-1 (canales VV, VH, ratio "
    "VH/VV, HAND) con F1-Score ≥ 0.90 e IoU ≥ 0.82. Ambos modelos alimentan un motor "
    "hidrológico de propagación (modelo conceptual HAND-bankfull calibrado por "
    "quebrada) que genera, cada hora del pronóstico, el estado de la mancha de "
    "inundación y su volumen desbordado (V = Σ h_i · A_i), la matriz de impacto "
    "espacial (edificios expuestos Google Open Buildings V3 y MS Building Footprints, "
    "vías GRIP4, suelos agrícolas ESA WorldCover clase 40) y el nivel de alerta "
    "VERDE/AMARILLO/ROJO según umbrales institucionales configurables. Todo se "
    "expone en la plataforma VEOX-FLOOD (FastAPI + PostgreSQL/PostGIS + Redis), con "
    "dashboards de mando 3D (CesiumJS con Cesium World Terrain, OSM Buildings y "
    "deck.gl) y una API REST documentada (OpenAPI) que ya opera sobre las 11 "
    "provincias de Piura y Tumbes en modo prototipo (TRL 3/4). Las alertas se "
    "distribuyen por SMS/WhatsApp (Twilio) y webhooks JSON a COER/Defensa Civil con "
    "mapa de la zona afectada adjunto (PDF). La metodología sigue cuatro objetivos "
    "(diseño de nodos y red; pipeline satelital y modelos de IA; integración y "
    "plataforma; validación operativa y transferencia), con un plan de validación "
    "que compara las predicciones contra aforos del ANA, ortofotos post-evento y "
    "reportes oficiales INDECI. El resultado es un TRL 6/7: prototipo en entorno "
    "relevante/operativo, dos temporadas de monitoreo continuo, una base de datos "
    "abierta FAIR, 2 artículos Q1/Q2, 1 tesis de maestría por objetivo y un producto "
    "con ruta comercial definida por el socio industrial."
)

PLANTEAMIENTO_PROBLEMA = (
    "El Fenómeno El Niño (FEN) es el peligro hidrometeorológico de mayor magnitud "
    "económica y humana en el Perú. El evento costero 2017 dejó 162 fallecidos, "
    "más de 1 millón de damnificados y pérdidas estimadas en S/. 9 162 millones "
    "(6.4 % del PBI sectorial); el departamento de Piura concentró ~40 % de los "
    "daños, con el distrito de Catacaos bajo más de 1.5 m de agua durante semanas. "
    "El evento 2023 reafirmó la exposición: los ríos Piura y Tumbes superaron sus "
    "caudales de diseño y colapsaron puentes y defensas ribereñas. La vulnerabilidad "
    "estructural se agrupa en tres carencias medibles. Primera: escasez de "
    "observación hidrológica en tiempo real. La red oficial de estaciones "
    "hidrométricas de la ANA en Piura y Tumbes es esparza, con transmisión "
    "satelital limitada y ventanas de latencia de horas; no existe una red pública "
    "densa de telemetría de nivel de río a escala de tramos urbanos (Catacaos, "
    "Tambogrande, Zarumilla), precisamente donde el lead time de evacuación se mide "
    "en minutos. Segunda: los métodos ópticos de mapeo satelital fallan durante el "
    "propio evento. La detección de agua con Sentinel-2/Landsat requiere cielos "
    "despejados, imposibles durante el FEN (cobertura nubosa >80 % por días), de "
    "modo que los mapas de inundación 'post-evento' llegan cuando la emergencia "
    "terminó; el radar Sentinel-1 sí atraviesa nubes, pero el país carece de un "
    "pipeline operativo que lo combine con topografía hidrológica (HAND) y lo "
    "convierta en producto de alerta. Tercera: los pronósticos oficiales son "
    "puntuales y no espaciales. Los avisos hidrológicos vigiles se emiten como "
    "umbrales de caudal en estaciones aisladas, sin predicción del área que se "
    "inundará ni del número de viviendas expuestas, lo que impide priorizar "
    "evacuaciones. La consecuencia agregada: lead time efectivo de alerta a la "
    "población inferior a 2 horas en 2017, frente a las 24–48 h que la evidencia "
    "internacional (p. ej., GFMS, GloFAS) considera alcanzables con fusión de "
    "telemetría, satélite y modelos de aprendizaje profundo. Adicionalmente, no "
    "existe en el mercado nacional un producto integrado in situ + satelital + IA "
    "que un municipio pueda adquirir: los sistemas internacionales no operan con "
    "datos locales ni se adaptan a la geometría administrativa peruana. VEOX-FLOOD "
    "ataca directamente estas carencias: red IoT densa y barata (nodo <USD 900) con "
    "doble vía de transmisión; pipeline SAR operativo en GEE con control de falsos "
    "positivos por HAND; predicción de nivel a 24–48 h con LSTM-attention y mapeo "
    "de la mancha con U-Net; plataforma con matriz de impacto sobre Open Buildings "
    "y GRIP4; y alertas institucionales trazables. El problema científico que se "
    "investiga es la fusión multimodal en tiempo real de observaciones heterogéneas "
    "(puntuales in situ, área satelital y pronóstico atmosférico) bajo incertidumbre "
    "— qué arquitectura y qué calidad de datos mínima permiten superar los umbrales "
    "de rendimiento (R² ≥ 0.85, F1 ≥ 0.90) en cuencas semiáridas con eventos de "
    "crecida relámpago — y el problema tecnológico es la ingeniería de ese sistema "
    "hasta TRL 6/7 validado durante dos temporadas de lluvias reales."
)

JUSTIFICACION = (
    "Justificación socioeconómica. Cada sol invertido en alerta temprana evita, "
    "según la estimación del Global Commission on Adaptation, entre 4 y 10 soles de "
    "pérdidas. Escalado a Piura: el FEN 2017 produjo S/. 4 200 millones de pérdidas "
    "departamentales; una reducción del 10 % atribuible a 24 h de lead time "
    "equivale a S/. 420 millones, tres órdenes de magnitud sobre el presupuesto de "
    "este proyecto (S/. 500 000). El beneficio se materializa en: evacuaciones "
    "oportunas (Catacaos tiene 45 000 habitantes en zona inundable), protección de "
    "la cadena agroexportadora del valle del Chira y del Río Piura (mango, cacao, "
    "limón: USD 400 millones/año regionales), continuidad de la Panamericana y de "
    "la vía Piura–Catacaos, y reducción del riesgo de brotes epidémicos "
    "post-inundación (dengue, leptospirosis). El sistema genera además empleo "
    "técnico calificado y capacidades permanentes en dos regiones históricamente "
    "atendidas solo en emergencia. Justificación tecnológica y científica. (1) "
    "Contribución científica: la fusión LSTM-attention (series puntuales) + U-Net "
    "(segmentación espacial SAR) + HAND (geomorfología) sobre cuencas semiáridas "
    "peruanas es un problema de investigación abierto; la literatura internacional "
    "reporta resultados excelentes en cuencas grandes y bien instrumentadas "
    "(GloFAS, GloFAS-ERA5), pero escasos en cuencas costeras pequeñas con crecidas "
    "relámpago, exactamente el caso Piura/Tumbes. Publicaremos la primera serie de "
    "modelos validados para estas cuencas y un dataset abierto FAIR. (2) Madurez y "
    "riesgo tecnológico controlado: el proyecto no parte de cero. El prototipo "
    "VEOX-FLOOD ya corre en modo TRL 3/4 con: ingesta GEE Sentinel-1 (Otsu+HAND) "
    "operativa sobre 11 provincias; motor hidrológico de propagación horaria "
    "calibrado por bankfull; matriz de impacto con Google Open Buildings V3, MS "
    "Building Footprints, GRIP4 y WorldCover; dashboards 3D (CesiumJS + deck.gl) y "
    "API FastAPI con suite de 17 pruebas automatizadas en verde; y canales de "
    "alerta Twilio/Webhook integrados. El riesgo tecnológico se concentra en la "
    "fiabilidad de campo de los nodos IoT y en la generalización de los modelos de "
    "IA, ambos con planes de mitigación explícitos. (3) Alineación con políticas: "
    "Plan Nacional de Adaptación al Cambio Climático (NAP, medidas 5 y 6 sobre "
    "riesgo hidrometeorológico), Plan Nacional de Gestión del Riesgo de Desastres "
    "(PLANAGERD 2014–2033, componente 2), Plan Bicentenario (ODS 11.5, 13.1) y la "
    "Política de Alerta Temprana del CENEPRED, que exige exactly la articulación "
    "multifuente que este proyecto entrega. (4) Sostenibilidad: VEOX S.A.C. asume "
    "la ruta comercial (licenciamiento municipal y a aseguradoras) y la operación "
    "24/7 post-proyecto, con costos de operación estimados en USD 1 200/mes por "
    "cuenca, cubribles por el ahorro evitado de un solo evento menor."
)

NOVEDAD_INNOVACION = (
    "1. Fusión multimodal inédita en el Perú: primer sistema que combina telemetría "
    "IoT hidrológica (LoRaWAN/4G), radar Sentinel-1 procesado en Google Earth "
    "Engine, precipitación IMERG y pronóstico horario, alimentando en conjunto a "
    "modelos de aprendizaje profundo. Los sistemas existentes usan una sola fuente.\n"
    "2. Control topográfico de falsos positivos: umbralización de Otsu + filtro HAND "
    "(MERIT Hydro) sobre Sentinel-1 redujo en el prototipo el agua espuria por "
    "sombra radar en laderas; su parametrización por cuenca (upa ≥ 25 km² para la "
    "red de drenaje) es una contribución metodológica replicable.\n"
    "3. Motor hidrológico HAND-bankfull interactivo: separa el caudal contenido en "
    "el cauce (bankfull calibrable por río: Chira 2.5 m) del desborde sobre la "
    "llanura, con lámina por celda h = max(0, h_cauce − bankfull − HAND) y volumen "
    "V = Σ h_i·A_i cada hora del pronóstico — superficie de inundación dinámica en "
    "3D (CesiumJS) inexistente en plataformas nacionales.\n"
    "4. Matriz de impacto georreferenciada en tiempo real: viviendas afectadas "
    "(Open Buildings V3 / MS Buildings), vías cortadas (GRIP4) y hectáreas agrícolas "
    "(WorldCover), convertidas directamente en niveles VERDE/AMARILLO/ROJO.\n"
    "5. Trazabilidad institucional: cada alerta SMS/WhatsApp incrusta la captura 3D "
    "del foco y un payload JSON hacia COER/Defensa Civil (webhook), cumpliendo el "
    "ciclo de alerta temprana del SINAGERD.\n"
    "6. Ruta de mercado: el diseño industrial y la plataforma corren por VEOX "
    "S.A.C., que licenciará el sistema — producto nacional con potencial de "
    "exportación a países andinos con exposición similar."
)

OBJETIVO_GENERAL = (
    "Desarrollar y validar en entorno operativo (TRL 6/7) un sistema inteligente "
    "multimodal de alerta temprana de inundaciones dinámicas para las cuencas de "
    "los ríos Piura y Tumbes, que integre una red piloto de nodos IoT hidrológicos, "
    "teledetección satelital SAR (Sentinel-1) procesada con control topográfico "
    "HAND, y modelos de aprendizaje profundo (LSTM-attention y U-Net), operando "
    "sobre una plataforma cloud con dashboards 3D, API abierta y alertas "
    "institucionales trazables, con métricas de desempeño certificadas R² ≥ 0.85 y "
    "RMSE ≤ 0.15 m en la predicción de nivel a 24–48 h, y F1-Score ≥ 0.90 / IoU "
    "≥ 0.82 en la segmentación de agua, durante dos temporadas de lluvias (FEN)."
)

OBJETIVOS_ESPECIFICOS = [
    (
        "OE1. Diseñar, fabricar y desplegar una red piloto de 8 nodos IoT "
        "hidrológicos autónomos (radar 80 GHz / ultrasonido de nivel, pluviómetro de "
        "cubeta, transmisión híbrida LoRaWAN 915 MHz / GPRS-4G, energía solar) en "
        "los puntos de control hidrológico de las cuencas de Piura (Catacaos, "
        "Tambogrande) y Tumbes (Zarumilla), con disponibilidad de telemetría ≥ 95 % "
        "por temporada de lluvias y latencia media ≤ 5 min."
    ),
    (
        "OE2. Implementar y validar el pipeline satelital Sentinel-1 en Google Earth "
        "Engine (umbralización de Otsu + filtro HAND ≤ 15 m + red de drenaje por área "
        "upstream) y entrenar la red U-Net de segmentación de agua libre sobre mosaicos "
        "multicanal (VV, VH, VH/VV, HAND), alcanzando F1-Score ≥ 0.90 e IoU ≥ 0.82 "
        "contra máscaras verificadas con ortofotos y datos del ANA."
    ),
    (
        "OE3. Desarrollar y entrenar el modelo LSTM con mecanismo de atención para la "
        "predicción probabilística del nivel/caudal de los ríos Piura y Tumbes a 24 y "
        "48 horas, fusionando telemetría IoT, IMERG y variables atmosféricas, con "
        "R² ≥ 0.85, RMSE ≤ 0.15 m y NSE ≥ 0.80 en particiones de prueba out-of-sample."
    ),
    (
        "OE4. Integrar los modelos en la plataforma cloud VEOX-FLOOD (motor de "
        "propagación HAND-bankfull por hora del pronóstico, matriz de impacto sobre "
        "Open Buildings/GRIP4/WorldCover, dashboards 3D CesiumJS/deck.gl, API REST "
        "OpenAPI, alertas Twilio SMS/WhatsApp y webhooks COER) y elevar la madurez "
        "del sistema de TRL 3/4 a TRL 6/7 con despliegue operativo continuo."
    ),
    (
        "OE5. Validar el sistema integral en dos temporadas de lluvias (campañas de "
        "aforo concurrentes, eventos reales FEN) mediante comparación contra estaciones "
        "del ANA, ortofotos post-evento y registros INDECI; certificar las métricas "
        "operativas (lead time, tasa de acierto de alerta, falsas alarmas), publicar "
        "los resultados en revistas indexadas y liberar el dataset y el código bajo "
        "estándares FAIR."
    ),
]

ESTADO_DEL_ARTE = (
    "Teledetección SAR de inundaciones. El radar de apertura sintética es el estándar "
    "de facto para mapeo de agua bajo nubosidad: el agua lisa actúa como reflector "
    "especular y presenta retrodispersión baja en banda C (5.405 GHz). Desde Henry "
    "et al. (2006) la umbralización de la banda VH/VV es la técnica dominante; la "
    "selección automática del umbral por el método de Otsu (1979) maximiza la "
    "varianza entre clases y es robusta a escenas heterogéneas. El error principal "
    "es la confusión entre agua y sombra radar en relieves accidentados; la "
    "literatura (Rennó et al. 2008) demostró que el índice HAND — altura sobre el "
    "drenaje más cercano derivada de un DEM — separa hidrológicamente las llanuras "
    "inundables de las laderas, y los flujos recientes (Salamone et al. 2023) lo "
    "usan como máscara de filtro. Nuestro pipeline (ya implementado en Google Earth "
    "Engine) aplica exactamente esa combinación Otsu+HAND y añade la red de drenaje "
    "por área upstream (upa) para el trazado del cauce, con resultados preliminares "
    "correctos en las cuencas de Piura y Tumbes (agua observada 89 563 ha en la "
    "provincia de Piura durante la validación 2026). Modelos de segmentación. Las "
    "redes encoder-decoder tipo U-Net (Ronneberger et al. 2015) superaron a la "
    "umbralización clásica en segmentación de agua sobre SAR (dataset Sen1Floods11, "
    "Bonafilia et al. 2020: F1 ~0.93 en múltiples biomas), especialmente cuando se "
    "incluyen canales auxiliares como HAND y el ratio VH/VV. La brecha: Sen1Floods11 "
    "contiene pocas cuencas andinas semiáridas y ninguna peruana; nuestros "
    "experimentos llenarán ese vacío con etiquetas verificadas por ortofotos. "
    "Predicción de nivel con aprendizaje profundo. Las redes LSTM (Hochreiter & "
    "Schmidhuber 1997) son el estado del arte en pronóstico de nivel/caudal a "
    "horizontes de horas-días: Kratzert et al. (2019) demostraron que una LSTM "
    "regional supera a modelos conceptualmente calibrados (HBV) en 531 cuencas "
    "CAMELS. El mecanismo de atención (Vaswani et al. 2017; Bahdanau et al. 2015) "
    "mejora el desempeño en horizontes largos (24–48 h) al ponderar los pasos "
    "temporales más informativos, y los trabajos de Fusión con precipitación "
    "satelital IMERG (Zhang et al. 2020) reportan NSE > 0.80 en ríos tropicales. "
    "Para cuencas costeras peruanas no existen publicaciones de LSTM-attention "
    "validadas; el régimen extremo del FEN (crecidas de 10× el caudal medio en "
    "horas) plantea una distribución de cola pesada que exige además funciones de "
    "pérdida robustas (Huber) y ponderación de eventos. Sistemas integrados. "
    "GloFAS (Copernicus EMS) y GFMS (NASA) proveen alerta global pero a "
    "resoluciones gruesas (5–10 km) y sin calibración local; los sistemas "
    "nacionales de alerta temprana en Perú (SENAMHI) operan con estaciones "
    "puntuales y umbrales fijos, sin mapeo espacial de la inundación ni matriz de "
    "exposición. En el plano comercial, plataformas privadas (FloodMapp, Iceye) "
    "demuestran la demanda pero con costos inaccesibles para municipios peruanos. "
    "La síntesis del estado del arte confirma: (i) la técnica Otsu+HAND+U-Net está "
    "madura pero no calibrada para Piura/Tumbes; (ii) la predicción LSTM-attention "
    "fusionada con IoT+IMERG es prometedora y sin validación local; y (iii) la "
    "integración operativa de todo ello en una plataforma con alerta institucional "
    "y matriz de impacto es un vacío tanto científico como de mercado. VEOX-FLOOD "
    "se posiciona exactamente en esa intersección, con un prototipo TRL 3/4 ya "
    "funcionando que reduce el riesgo del proyecto."
)

TRL_INGRESO = "TRL 3/4 (comprobación analítica y experimental de las funciones críticas)"
TRL_INGRESO_FUNDAMENTO = (
    "El prototipo VEOX-FLOOD ya implementa y demuestra en operación: (i) ingesta "
    "Sentinel-1 con Otsu+HAND sobre 11 provincias (endpoint /api/geo/simulate con "
    "respuesta < 30 s por provincia, datos reales de GEE); (ii) motor de propagación "
    "horaria HAND-bankfull con serie de 6 h validada físicamente (crecida al cruzar "
    "bankfull en h=3); (iii) matriz de impacto con Open Buildings/MS Buildings "
    "(2 000 huellas por provincia), GRIP4 y WorldCover; (iv) visor 3D CesiumJS con "
    "World Terrain, OSM Buildings, drenaje 3D con partículas y animación de "
    "propagación; (v) API FastAPI con 17 pruebas automatizadas en verde (17/17 "
    "passed) y canales Twilio/Webhook COER integrados; (vi) análisis multi-zona "
    "Piura/Tumbes con resultados ROJO certificados (Piura: 278.9 M m³, 53 784 ha, "
    "310 vías; Tumbes: 65.3 M m³, 11 145 ha). Lo que NO existe aún: los nodos IoT "
    "físicos, los modelos de IA entrenados con datos locales y la validación en "
    "temporada de lluvias. Eso define el trabajo del proyecto."
)
TRL_SALIDA = "TRL 6/7 (prototipo demostrado en entorno relevante y operativo en temporada de lluvias)"
TRL_SALIDA_FUNDAMENTO = (
    "Al cierre del proyecto se habrá demostrado el sistema completo — nodos IoT "
    "desplegados (8), pipeline SAR operativo, modelos de IA con métricas certificadas "
    "(R² ≥ 0.85, F1 ≥ 0.90), plataforma con alertas institucionales emitidas y "
    "registradas — durante dos temporadas de lluvias reales (diciembre–marzo), con "
    "informes de operación por evento (lead time, tasa de acierto) avalados por las "
    "municipalidades y el COER de Piura y Tumbes. La diferencia entre TRL 6 y 7 "
    "(demostración en entorno operativo) se cubre con la operación continua 24/7 "
    "durante la segunda temporada y el traspaso de la operación a VEOX S.A.C., que "
    "licenciará el producto a municipios."
)

METODOLOGIA = (
    "Metodología en cinco objetivos con flujos secuenciales e iterativos (sprints de "
    "ingeniería + ciclos de validación científica), coordinados por PMO/MLOps mensual.\n\n"
    "OE1 — Red IoT hidrológica. (1.1) Ingeniería del nodo: radar de nivel 80 GHz "
    "(±2 mm, alcance 15 m) como primario, ultrasonido 42 kHz de respaldo; pluviómetro "
    "de cubeta 0.2 mm; MCU ESP32-S3 + GNSS; LoRa SX1262 (915 MHz, +22 dBm) y LTE "
    "Cat-M1; energía solar 10 W + batería LiFePO₄ 20 Ah (autonomía 14 días); carcaza "
    "IP67 anticorrosiva. (1.2) Comunicación: gateways LoRaWAN ChirpStack en Catacaos "
    "y Zarumilla (radio ~8 km) con fallback 4G; payload binario 12 bytes/lectura "
    "(10 min). (1.3) Despliegue: 8 nodos — Piura: puente Piura–Catacaos, Tambogrande, "
    "Sechura–Vice; Tumbes: Zarumilla internacional, San Jacinto, Guineal; + 2 móviles "
    "de respaldo. Georreferenciación GNSS diferencial y cota ANA. (1.4) Banco de "
    "pruebas UTEC: calibración contra limnímetro/vertedero (incertidumbre ±5 mm).\n\n"
    "OE2 — Pipeline satelital y U-Net. (2.1) Ingesta GEE: COPERNICUS/S1_GRD IW GRDH "
    "VV/VH; dB; ratio VH/VV; umbral de Otsu sobre VH; máscara HAND ≤ 15 m (MERIT "
    "Hydro: hnd/elv/upa); matrices NumPy alineadas (EPSG:4326, 100 m regional / 30 m "
    "focal). (2.2) Dataset: pases co-evento con ortofotos post-FEN y máscaras ANA; "
    "etiquetado semiautomático (QGIS); partición espacial 70/15/15 por bloques. "
    "(2.3) Entrenamiento U-Net: 6 canales (VV, VH, ratio, HAND, pendiente, upa); "
    "encoder 4 niveles (64→512) + decoder con skip connections; pérdida Dice+BCE; "
    "AdamW (lr 1e-4, cosine); augmentation geométrico y speckle; CV espacial 5-fold. "
    "(2.4) Métricas: F1 ≥ 0.90, IoU ≥ 0.82, curvas PR, ablation study (sin HAND, sin "
    "ratio). (2.5) Comparación contra Otsu+HAND clásico y Global Surface Water.\n\n"
    "OE3 — LSTM-attention 24–48 h. (3.1) Entradas: series 10-min de nivel (z-score), "
    "IMERG 30-min por cuenca, Open-Meteo/ECMWF horario, estáticas (upa, HAND medio). "
    "(3.2) Arquitectura: encoder LSTM 2 capas (256/128) + atención aditiva (Bahdanau) "
    "sobre ventana 72 h + decoder emisor de trayectoria 48 h; cabezas de cuantiles "
    "10/50/90 (pinball loss). (3.3) Entrenamiento: splits out-of-sample (2026 entrena, "
    "2027 prueba), Huber+pinball, early stopping 15, Optuna 50 trials. (3.4) Métricas: "
    "R² ≥ 0.85, RMSE ≤ 0.15 m, NSE ≥ 0.80, MAE ≤ 0.10 m; de evento: POD ≥ 0.85, FAR "
    "≤ 0.20, CSI ≥ 0.75. (3.5) Interpretabilidad: mapas de atención y SHAP agregado "
    "para confianza de operadores del COER.\n\n"
    "OE4 — Integración y plataforma VEOX-FLOOD. (4.1) Cloud: FastAPI con endpoints "
    "(/zones, /api/geo/simulate, /forecast, /forecast-timeline, /simulate-and-alert, "
    "/api/alert/trigger, /api/report/pdf); PostgreSQL/PostGIS; Redis; workers GEE. "
    "(4.2) Motor HAND-bankfull: 7 pasos horarios re-simulando h = max(0, h_cauce(t) "
    "− bankfull − HAND); V = Σ h_i·A_i; máscaras serializadas para animación; "
    "bankfull por río (Chira 2.5, Tumbes 3.0, Piura 1.8 m). (4.3) Impacto: Open "
    "Buildings V3/MS Buildings (≥0.15 m), GRIP4 (≥0.20 m), WorldCover clase 40. "
    "(4.4) Frontends: dashboard COE (Streamlit) y Centro de Mando 3D (CesiumJS + World "
    "Terrain + OSM Buildings + deck.gl) con hotspots flyTo y partículas de flujo. "
    "(4.5) Alertas: motor VERDE/AMARILLO/ROJO configurable, Twilio SMS/WhatsApp con "
    "captura incrustada, webhook JSON a COER, PDF automático. (4.6) Operación 24/7: "
    "HTTPS/JWT, backups diarios, Prometheus/Grafana, SLA ≥ 99 %.\n\n"
    "OE5 — Validación y transferencia. (5.1) Campañas de aforo ADCP en 4 secciones "
    "(8 campañas, 2 temporadas), con ANA. (5.2) Verificación contra ortofotos y "
    "aguaniveles GPS. (5.3) Métricas por evento: lead time, POD/FAR/CSI, disponibilidad. "
    "(5.4) Simulacros de mesa con COER Piura/Tumbes y capacitación municipal. (5.5) "
    "Transferencia: manuales, licenciamiento VEOX, 2 artículos Q1/Q2 (Journal of "
    "Hydrology, RSE, Natural Hazards), liberación FAIR (Zenodo DOI) y 2 tesis de "
    "maestría.\n\n"
    "Gestión de riesgos transversal: riesgos por OE con mitigación (tabla), comité "
    "técnico mensual UTEC–VEOX y KPI trimestrales a PROCIENCIA."
)

# ===========================================================================
# 10. VIABILIDAD, CRONOGRAMA Y RIESGOS
# ===========================================================================
CRONOGRAMA = [
    ("M1–M3",  "OE1.1–1.2: ingeniería del nodo IoT y banco de pruebas; OE2.1: pipeline GEE en producción", "UTEC+VEOX"),
    ("M2–M6",  "OE1.3: fabricación de 8 nodos; OE2.2: dataset etiquetado v1", "VEOX+UTEC"),
    ("M5–M8",  "OE1.4: despliegue en Piura (4 nodos) y Tumbes (4 nodos); OE3.1–3.2: dataset LSTM", "VEOX+UTEC"),
    ("M6–M12", "OE2.3–2.5: entrenamiento U-Net y métricas F1/IoU", "UTEC"),
    ("M9–M15", "OE3.3–3.5: entrenamiento LSTM-attention y certificación de métricas", "UTEC"),
    ("M10–M18","OE4.1–4.6: integración plataforma, motor HAND-bankfull calibrado, alertas operativas", "VEOX"),
    ("M12–M14","Temporada de lluvias #1: validación en vivo + campaña de aforo #1–2", "Todos"),
    ("M15–M17","Ajustes de modelos y recalibración bankfull por río", "UTEC"),
    ("M18–M20","Temporada de lluvias #2: operación continua 24/7 + campaña de aforo #3–4", "Todos"),
    ("M20–M23","OE5: certificación de métricas, artículos Q1/Q2, liberación FAIR, tesis", "UTEC"),
    ("M23–M24","Transferencia a VEOX S.A.C., manuales, cierre y informe final", "VEOX+UTEC"),
]

RIESGOS = [
    ("Técnico", "Pérdida de telemetría IoT por vandalismo o clima severo", "Media", "Alto",
     "Carcaza IP67 antivandalismo, anclaje en infraestructura municipal vigilada, respaldo GPRS, 2 nodos móviles de repuesto, SLA de reparación < 72 h."),
    ("Técnico", "Latencia o indisponibilidad de Sentinel-1 (revisita 6–12 días)", "Media", "Medio",
     "Complementar con Sentinel-1 de órbitas cruzadas, IMERG para detección de lluvia inmediata, y radiosondeo del cauce in situ por los nodos."),
    ("Científico", "Los modelos de IA no alcanzan R² ≥ 0.85 / F1 ≥ 0.90", "Media", "Alto",
     "Abandono gradual de arquitectura (LSTM → Transformer); aumento de datos con transferencia de Sen1Floods11; revisión de particiones espaciales; comité científico de contingencia en M12."),
    ("Operativo", "FEN no se activa durante la ventana del proyecto (años neutrales)", "Alta", "Medio",
     "Validación con eventos de crecida menor (hulladas ordinarias), inyección de escenarios sintéticos calibrados con historial 1983/1998/2017, ejercicio de mesa con COER."),
    ("Institucional", "Retraso en permisos municipales / ANA para instalación de nodos", "Media", "Medio",
     "Convenios marco firmados en M1; carta de no objeción previa a la postulación; plan B de ubicación alterna en cada punto."),
    ("Financiero", "Variación cambiaria USD/PEN afecta importación de sensores", "Media", "Bajo",
     "Provisión de 5 % en el presupuesto de equipamiento; compras agrupadas; alternativas nacionales de sensores validadas."),
    ("Datos", "Pérdida de datos por falla de storage cloud", "Baja", "Alto",
     "Backups diarios multi-región (PostgreSQL PITR + snapshots GCS), replicación del dataset FAIR en Zenodo (DOI) y repositorio UTEC."),
    ("Equipo", "Rotación de tesistas o personal clave", "Media", "Medio",
     "Documentación continua, pares de respaldo por rol, contratos con plazos definidos y cláusulas de permanencia."),
]

# ===========================================================================
# 11. RESULTADOS ESPERADOS
# ===========================================================================
RESULTADOS_OBLIGATORIOS = [
    "Artículos científicos: 2 publicaciones en revistas indexadas Q1/Q2 (Scopus/WoS) sobre fusión SAR+HAND+U-Net y LSTM-attention para predicción de nivel en cuencas semiáridas.",
    "Capital humano: 2 tesis de maestría sustentadas y graduados en Ciencia de Datos / Ingeniería (UTEC), con tesis directamente derivadas del proyecto.",
    "Dataset abierto FAIR: serie hidrometeorológica de 2 temporadas (8 nodos × 10 min), máscaras de agua etiquetadas, y pesos de los modelos, publicados en Zenodo con DOI y fichas de datos.",
    "Código fuente abierto: repositorio del pipeline GEE, modelos y plataforma (licencia MIT/Apache-2.0) con documentación y DOI en Zenodo.",
]

RESULTADOS_TECNOLOGICOS = [
    "Prototipo VEOX-FLOOD TRL 6/7: sistema integral (nodos IoT + pipeline SAR + modelos de IA + plataforma + alertas) operando 24/7 durante la temporada de lluvias #2 en Piura y Tumbes.",
    "8 nodos IoT hidrológicos fabricados y desplegados con disponibilidad ≥ 95 % por temporada.",
    "Plataforma cloud VEOX-FLOOD/SAMPLING.AI con dashboards 3D, API REST documentada (OpenAPI) y servicio de alertas masivas SMS/WhatsApp/Webhook institucional.",
    "Producto con ruta comercial: licenciamiento a ≥ 2 municipalidades o entidades del sector público al cierre del proyecto (cartas de intención).",
    "Sistema de indicadores de alerta temprana VERDE/AMARILLO/ROJO integrado al protocolo del COER de Piura y Tumbes (convenio firmado).",
    "Manual técnico y de operación + capacitación a ≥ 20 operadores municipales y del COER.",
]

INDICADORES_RESULTADOS = [
    ("Publicaciones indexadas", "2 artículos Q1/Q2 enviados/aceptados", "M23"),
    ("Tesis de maestría", "2 sustentadas", "M24"),
    ("Dataset FAIR", "1 DOI Zenodo (series + máscaras + pesos)", "M22"),
    ("Disponibilidad de red IoT", "≥ 95 % por temporada", "M20"),
    ("Latencia de telemetría", "≤ 5 min media", "M20"),
    ("Precisión de pronóstico", "R² ≥ 0.85; RMSE ≤ 0.15 m (h24 y h48)", "M15 y M20"),
    ("Segmentación U-Net", "F1 ≥ 0.90; IoU ≥ 0.82", "M12 y M20"),
    ("Lead time de alerta ROJO", "≥ 6 h promedio por evento", "M20"),
    ("Tasa de falsas alarmas (FAR)", "≤ 0.20", "M20"),
    ("Disponibilidad de plataforma", "≥ 99 %", "M18"),
    ("Operadores capacitados", "≥ 20 (municipios + COER)", "M22"),
    ("Licenciamientos", "≥ 2 cartas de intención", "M24"),
]

# ===========================================================================
# 12. PLAN DE GESTIÓN DE DATOS (PGD) — FAIR / ALICIA 2.0.1
# ===========================================================================
PGD = {
    "Descripción de los datos": (
        "Datos de observación: series temporales de nivel de río (10 min, 8 nodos), "
        "lluvia in situ (0.2 mm resol.), geolocalización GNSS y metadatos de estación. "
        "Datos satelitales: escenas Sentinel-1 GRD (Copernicus, CC-BY), IMERG (NASA GPM), "
        "MERIT Hydro, Open Buildings, GRIP4, WorldCover. Datos derivados: máscaras de "
        "agua etiquetadas, predicciones de modelos, matrices de impacto, máscaras de "
        "propagación horaria. Metadatos Dublin-Core extendidos con diccionario de "
        "variables y unidad (SI)."
    ),
    "Recogida y reutilización": (
        "Reutilización: colecciones abiertas Copernicus/NASA/ESA (licencias CC-BY/CC0). "
        "Recogida: nodos IoT VEOX con calibración trazable; campañas de aforo ANA. "
        "Estándares: CF-Convention para series, OGC GeoJSON/GeoTIFF/COG para rasters, "
        "NetCDF para datasets multitemporales."
    ),
    "Documentación y calidad": (
        "Fichas de estación (posición, cota, calibraciones), bitácora de campañas, "
        "control de calidad automático (rango, spike, flatline) y manual deqc. "
        "Versionado semántico de datasets (v1.0, v1.1) con changelog."
    ),
    "Almacenamiento y respaldo": (
        "Primario: PostgreSQL/PostGIS + object storage con versionado; backups "
        "diarios incrementales + semanales completos, retención 5 años; replicación "
        "multi-región; snapshot inmutable pre-publicación."
    ),
    "Seguridad y ética": (
        "Acceso por roles (público/registrado/equipo); anonimización de números de "
        "contacto en las alertas; cumplimiento Ley 29733; sin datos sensibles de "
        "terceros; datos de emergencia con cláusula de uso institucional."
    ),
    "Compartición y acceso (FAIR)": (
        "Findable: DOI en Zenodo, metadatos ricos, indexación en DataCite. "
        "Accessible: descarga abierta HTTP (CC-BY 4.0 datos, MIT código), API REST "
        "pública. Interoperable: formatos abiertos (CSV/Parquet/COG/GeoJSON), "
        "vocabularios hidrológicos estándar. Reusable: licencias explícitas, "
        "provenance Git, contenedores Docker para reproducibilidad."
    ),
    "Responsabilidades y curación": (
        "IP: custodio científico; Data Steward UTEC: gestión técnica del repositorio; "
        "VEOX: operación cloud y SLA. Curación activa durante el proyecto y ≥ 5 años "
        "post-proyecto por el repositorio institucional UTEC."
    ),
    "Presupuesto de datos": (
        "USD 3 500 (storage + DOI + horas de data steward) incluidos en el rubro de "
        "servicios especializados."
    ),
}

# ===========================================================================
# 13. PRESUPUESTO (S/. 500 000,00)
# ===========================================================================
PRESUPUESTO = [
    ("1.1", "Personal de investigación (IP, co-investigadores, tesistas)", "180 000,00"),
    ("1.2", "Personal de apoyo (técnico de campo, data steward)", "30 000,00"),
    ("2.1", "Equipamiento: 8 nodos IoT (sensores, MCU, LoRa/4G, solar), gateway LoRaWAN, GPU para entrenamiento", "95 000,00"),
    ("2.2", "Software y licencias (cloud compute, Twilio API, GEE — no gratuito, MLOps)", "45 000,00"),
    ("3.1", "Materiales de consumo (electrónica, cables, repuestos, baterías)", "25 000,00"),
    ("4.1", "Campañas de campo (8 campañas: viáticos Piura/Tumbes, aforo, transporte)", "40 000,00"),
    ("4.2", "Publicación en revistas Q1/Q2 (APC) y difusión", "12 000,00"),
    ("4.3", "Servicios especializados (validación estadística externa, auditoría de seguridad, data steward)", "18 000,00"),
    ("5.1", "Gastos administrativos y de gestión (UTEC + VEOX, 8 %)", "40 000,00"),
    ("5.2", "Imprevistos (≤ 3 %)", "15 000,00"),
]

PRESUPUESTO_TOTAL = "S/. 500 000,00 (quinientos mil con 00/100 soles)"
