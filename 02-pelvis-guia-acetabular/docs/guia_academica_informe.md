# Guía académica de posicionamiento de copa acetabular (coxal derecho)

> **Aviso:** ejercicio académico con datos de un cadáver (VSD, licencia CC BY-NC-SA 4.0). **No es un dispositivo médico, no está validado y no debe usarse en pacientes.** Una guía quirúrgica real requiere el CT del paciente, la planificación de un cirujano, validación y cumplimiento regulatorio.

## Objetivo
Diseñar, de forma computacional, una guía que oriente el eje de una copa acetabular sobre el coxal derecho segmentado en 3D Slicer, con los ángulos objetivo habituales (zona de Lewinnek).

## Datos de partida
- Coxal derecho, coxal izquierdo y sacro: segmentación experta del CT público (Fischer, Sci Data 2023), depurada (isla única, huecos rellenos, suavizado).
- Archivos: `modelos/Hip_R.stl`, `Hip_L.stl`, `Sacrum.stl`.

## Método
1. **Acetábulo.** Ajuste de esfera (RANSAC + mínimos cuadrados) a la superficie del coxal alrededor de la cabeza femoral: centro (37.5, 118.5, 872.9) mm, radio 23.5 mm. Copa de referencia de **48 mm**.
2. **Sistema pélvico.** Plano pélvico anterior a partir de ambas espinas ilíacas anterosuperiores (ASIS) y el punto anterior de la sínfisis púbica. Los marcadores se detectaron de forma automática y aproximada.
3. **Eje objetivo.** Inclinación radiográfica **40°** y anteversión radiográfica **15°**. Comprobación inversa sobre el eje final: 40.00° y 15.00°. Verificado que el eje sale del acetábulo (vacío lateral) y que la pared medial es hueso.
4. **Geometría de la guía** (voxelizada a 0.7 mm):
   - 3 parches de contacto de 3 mm de espesor, que copian la superficie del hueso alrededor del borde acetabular (acimut 135°, −45° y −135°, elegidos por cobertura ósea y separación ≥ 80°).
   - Holgura guía–hueso de 0.3 mm.
   - Tubo guía alineado con el eje de la copa: Ø exterior 16 mm, orificio Ø 9.2 mm, largo 30 mm.
   - 3 puntales (Ø 5.2 mm) que unen el tubo con cada parche.
   - 3 orificios para clavijas Ø 2.6 mm, uno por parche.
5. **Mallas.** Marching cubes y suavizado; comprobación de mallas cerradas.

## Resultados
| Elemento | Valor |
|---|---|
| Guía | 63 188 triángulos · 13.4 cm³ · 0 aristas abiertas · una sola pieza |
| Área de contacto aproximada | ≈ 2 035 mm² |
| Copa de referencia (48 mm) | 41 392 triángulos · 0 aristas abiertas |
| Eje planificado | 6 388 triángulos |

## Uso conceptual de la guía
La guía se apoya en los tres parches. A través del orificio del tubo se pasaría una aguja o manguito de ≤ 4 mm a lo largo del eje planificado hasta la pared medial del acetábulo. La guía se retira y esa aguja orienta el fresado y la impactación de la copa.

## Limitaciones
- **Marcadores pélvicos automáticos y aproximados**; la planificación depende de ellos. El CT es en decúbito supino y no refleja la inclinación pélvica funcional.
- **Sin partes blandas, labrum ni cartílago:** el hueso es la única superficie de apoyo; en la realidad los parches deben apoyarse en hueso expuesto.
- **Puntales finos y largos (Ø 5.2 mm, ≈ 60 mm):** no he comprobado su rigidez; probablemente haya que engrosarlos o acortarlos. La superficie muestra escalones por la resolución del voxel.
- **Sin análisis de desviación angular** por mal asentamiento de la guía ni de tolerancias de impresión.
- **Sin validación experimental:** no se ha impreso ni probado sobre un modelo físico.
- Hueso de una persona de 95 años; la anatomía y la calidad ósea no son representativas de un paciente típico.

## Pasos necesarios antes de cualquier uso real
Validación de la segmentación sobre el CT del paciente; planificación firmada por el cirujano; análisis de sensibilidad (error de asentamiento, tolerancia de impresión); material biocompatible y esterilizable; impresión y verificación dimensional; ensayo sobre modelo físico o cadavérico; marco regulatorio aplicable.

## Archivos
- `guia_copa_acetabular.stl` — guía (mm, coordenadas RAS del CT)
- `copa_referencia_48mm.stl` — copa de referencia
- `eje_planificado.stl` — eje planificado
- `guia_plan.json` — parámetros y comprobaciones
- `guia_resumen_vistas.png`, `vista_1…4_*.png` — vistas
- `g1_guia.py` (diseño), `g2_render.py` (vistas)
