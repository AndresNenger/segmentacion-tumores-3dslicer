# Tumor cerebral: segmentación, análisis de tejido y plantilla de craneotomía (académico)

> **Aviso:** ejercicio académico con el dato de ejemplo **MRBrainTumor1** de 3D Slicer. No es un dispositivo médico, no es un diagnóstico y no debe usarse en pacientes.

## 1. Datos
- MRBrainTumor1 (datos de ejemplo de 3D Slicer): RM ponderada en T1 con contraste, 256 × 256 × 112, vóxel 0,94 × 0,94 × 1,4 mm. Checksum verificado.
- Lesión frontal izquierda, parasagital (junto a la hoz), bien delimitada y que realza con contraste.

## 2. Segmentación (Segment Editor)
1. Dos segmentos: **Tumor** y **Tejido sano**.
2. Trazos de semilla en 3 cortes axiales dentro del tumor y alrededor, en tejido sano (incluida la hoz), más cortes por encima y por debajo. Los trazos se generaron por script, al estilo del tutorial de PerkLab; no los pintó una persona a mano.
3. **Grow from seeds** → suavizado mediano de 3 mm → conservar la isla mayor.
4. Un umbral simple se "escapa" por la hoz y los vasos; las semillas de fondo lo evitan.

## 3. Resultados (Segment Statistics)
| Medida | Tumor | Sustancia blanca (referencia, hemisferio derecho) |
|---|---|---|
| Volumen | **16,94 cm³** | 0,93 cm³ (esfera de 6 mm) |
| Diámetro máximo (Feret) | **39,8 mm** | — |
| Redondez | 0,94 | — |
| Superficie | 3 408 mm² | — |
| Intensidad media | **179** | 91 |
| Desviación estándar | 24 | 4,4 |
| Coeficiente de variación | 13 % | 4,8 % |

El tumor realza unas **1,97 veces** más que la sustancia blanca y es más heterogéneo. Las intensidades de RM son unidades de señal, no propiedades del tejido; el realce no permite un diagnóstico (haría falta histología).

## 4. Planificación y plantilla de craneotomía
- **Trayectoria:** la más corta desde el centro del tumor a la piel, con entrada en el lado del tumor y a ≥ 15 mm de la línea media (seno sagital superior). Entrada paramediana izquierda, 22° respecto a la vertical, 38 mm del centro del tumor a la piel y unos 22 mm de la piel a la superficie del tumor.
- **Ventana:** envolvente convexa de la proyección del tumor + 10 mm de margen, unos 54 mm de diámetro máximo.
- **Plantilla:** carcasa de 3 mm que copia el cuero cabelludo (holgura de 0,3 mm), con un apoyo de 22 mm alrededor de la ventana. La superficie de la cabeza se suavizó (σ = 3 mm) para eliminar un surco por caída de señal y un objeto externo pegado al cuero cabelludo en la RM.
- **Comprobaciones:** 0 vóxeles de la plantilla dentro de la cabeza; distancia mínima ventana–silueta del tumor de 10,0 mm; mallas cerradas.

## 5. Impresión 3D (OrcaSlicer, Creality K1C, PLA, capa 0,16 mm, 3 paredes, 20 % de relleno, soportes automáticos)
| Pieza | Orientación | Voladizo | Tiempo estimado | Material |
|---|---|---|---|---|
| Plantilla | de canto | 1,9 % | 1 h 45 min | 20,9 cm³ |
| Maniquí de cuero cabelludo (base plana) | base sobre la cama | 0,2 % | 2 h 29 min | 43,4 cm³ |
| Modelo del tumor 1:1 | mínimo voladizo | 8,2 % | 41 min | 7,3 cm³ |

Espesor de la plantilla: mediana 3,3 mm, mínimo 2,4 mm. Estimaciones de un laminado de prueba con perfiles genéricos.

## 6. Limitaciones
- Un solo caso de ejemplo; la segmentación no se comparó con una segmentación experta de referencia.
- Las semillas se generaron por script; la segmentación es semiautomática, no manual.
- La plantilla se apoya en el cuero cabelludo, que es deformable; una guía real se apoyaría en hueso y se validaría con neuronavegación.
- No se modelaron hueso, vasos ni áreas elocuentes; el criterio de trayectoria es geométrico y simplificado.

## 7. Archivos
- Videos: `brain_tumor_full_EN.mp4` (2 min 24 s) y `brain_tumor_60s_EN.mp4` (60 s), con subtítulos en inglés.
- Segmentación: `segmentacion_tumor.seg.nrrd`; estadísticas: `estadisticas_segmentos.json`.
- Plan: `plan_craneotomia.json`; vistas: `plantilla_resumen_vistas.png`.
- Impresión: `imprimir_plantilla.stl`, `imprimir_maniqui.stl`, `imprimir_tumor.stl`, `placa_craneotomia.3mf`, `orca_out\*_k1c.gcode`.
