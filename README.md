# Segmentación de tumores, guías quirúrgicas académicas y simulación en realidad mixta

Proyecto académico que va de una imagen médica (resonancia o tomografía) a un modelo 3D, un análisis, una pieza impresa y un simulador. Todo se hizo con software abierto: **3D Slicer**, **Python**, **Blender**, **OrcaSlicer** y **three.js / WebXR**.

> **Aviso:** son ejercicios académicos con datos públicos de ejemplo. **No son dispositivos médicos, no sirven para diagnosticar ni para decidir tratamientos, y no deben usarse en pacientes.** Una guía quirúrgica real necesita las imágenes del paciente, el plan de un cirujano, validación y aprobación regulatoria.

## Contenido

| Carpeta | Qué hay |
|---|---|
| [`04-tutorial-3dslicer`](04-tutorial-3dslicer) | **Empieza aquí.** Tutorial para estudiantes sin experiencia: segmentar un tumor cerebral paso a paso, con capturas marcadas y scripts para recrearlas y generar el video. |
| [`05-tutorial-documento-word`](05-tutorial-documento-word) | Tutorial técnico completo en Word y PDF (29 páginas) con el flujo de punta a punta. |
| [`01-tumor-cerebral`](01-tumor-cerebral) | Segmentación del tumor, análisis de tejido, plantilla de craneotomía, impresión 3D y simulador WebXR para Meta Quest 3. |
| [`02-pelvis-guia-acetabular`](02-pelvis-guia-acetabular) | Segmentación de la pelvis, análisis de elementos finitos (200 kN) y guía para orientar la copa acetabular. |
| [`03-femur-fea`](03-femur-fea) | Extracción del fémur, malla sólida y análisis de elementos finitos (100 N de compresión). |
| [`06-comparacion-dos-estudios`](06-comparacion-dos-estudios) | Registro de dos resonancias del mismo paciente, segmentación del tumor en cada una y comparación (Dice, volumen). |
| [`08-tutorial-simulacion-vr`](08-tutorial-simulacion-vr) | Tutorial paso a paso del simulador de craneotomía en VR: cómo usarlo (5 pasos y fisiología) y cómo se construyó. |
| [`09-pose-tracker`](09-pose-tracker) | Cuaderno de Colab que mide ángulos articulares con MediaPipe (fisioterapia, ergonomía, deporte). |
| [`07-ejemplos-cnn-imagen-medica`](07-ejemplos-cnn-imagen-medica) | De la segmentación manual a las CNN: una U-Net 2D probada y enlaces a MONAI, nnU-Net y MedMNIST. |

## Simulador en línea

**https://andresnenger.github.io/segmentacion-tumores-3dslicer/** — el simulador de craneotomía se abre directamente en el navegador (GitHub Pages da HTTPS, que WebXR exige). En unas Meta Quest 3, abre esa dirección en el Meta Quest Browser y pulsa *Enter VR* o *Enter passthrough*. Sigue sin estar probado en las gafas.

Otro repositorio relacionado: [generador-tutoriales-3dslicer](https://github.com/AndresNenger/generador-tutoriales-3dslicer), con las herramientas para hacer los videos de tutorial.

## Resultados principales (tumor cerebral)

- Volumen del tumor: **16,94 cm³**, diámetro máximo 39,8 mm, redondez 0,94.
- Intensidad media 179 frente a 91 en sustancia blanca (≈ 2×).
- Trayectoria paramediana a ≥ 15 mm de la línea media; ventana de craneotomía de ≈ 54 mm.
- Plantilla impresa en ≈ 1 h 45 min (Creality K1C, PLA, estimado con un perfil genérico).

## Cómo empezar

1. Instala [3D Slicer](https://download.slicer.org) (probado con 5.12.4).
2. Abre `04-tutorial-3dslicer/documentos/Tutorial_segmentar_tumor_3DSlicer.docx` y sigue los pasos.
3. Para el simulador: usa el enlace de arriba, o abre `01-tumor-cerebral/simulador-quest/Craniotomy_Trainer_Quest3.html` en un navegador (instrucciones para las Quest en `LEEME.txt`).

## Datos que NO están en el repositorio

Los datos de entrada son grandes o tienen licencia propia, así que se descargan aparte:

| Dato | De dónde | Licencia |
|---|---|---|
| MRBrainTumor1 (resonancia con tumor) | Módulo *SampleData* de 3D Slicer, o [SlicerTestingData](https://github.com/Slicer/SlicerTestingData) | datos de ejemplo de 3D Slicer |
| CT de pelvis y muslos con segmentación experta (carpeta 02 y 03) | [VSDFullBodyBoneReconstruction en Zenodo](https://zenodo.org/records/8302449) | CC BY-NC-SA 4.0 |
| CT de cuerpo completo VSDFullBody | [Zenodo](https://zenodo.org/records/8270365) | CC BY-NC-SA 4.0 |

Crédito de los datos de huesos: Fischer, M.C.M. *Database of segmentations and surface models of bones of the entire lower body created from cadaver CT scans.* Scientific Data 10, 763 (2023).

**Uso no comercial:** los resultados derivados de esos CT (mallas de huesos y análisis) heredan la licencia CC BY-NC-SA 4.0. Por eso este repositorio no incluye esas mallas; se regeneran con los scripts.

## Qué falta y limitaciones

- Un solo caso por ejercicio; las segmentaciones no se validaron contra una referencia experta.
- Las semillas del tutorial se generan por script; en el documento se explica cómo pintarlas a mano.
- El simulador se probó en un navegador de PC, **no con unas Meta Quest 3**.
- Los scripts tienen rutas de Windows escritas dentro (`C:/Users/Laboratorio/...`): cámbialas por las tuyas antes de ejecutarlos.
- Los videos no están aquí por su peso (se publican en YouTube y TikTok).

## Licencia

- **Código** (`.py`, `.js`, `.html`): MIT, ver [`LICENSE`](LICENSE).
- **Documentos, capturas y textos:** CC BY 4.0.
- **Datos y mallas derivadas de los CT de cadáver:** CC BY-NC-SA 4.0, ver [`NOTICE.md`](NOTICE.md).
