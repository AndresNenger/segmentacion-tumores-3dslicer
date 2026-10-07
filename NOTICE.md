# Avisos sobre datos y licencias

## Datos de huesos (carpetas 02 y 03)

Los análisis de pelvis y fémur parten de tomografías postmortem del repositorio VSDFullBody / VSDFullBodyBoneReconstruction (Zenodo), con segmentaciones de huesos de las extremidades inferiores.

- Origen: https://zenodo.org/records/8302449 y https://zenodo.org/records/8270365
- Licencia: **Creative Commons Atribución-NoComercial-CompartirIgual 4.0 (CC BY-NC-SA 4.0)**
- Crédito: Fischer, M.C.M. *Database of segmentations and surface models of bones of the entire lower body created from cadaver CT scans.* Scientific Data 10, 763 (2023). Datos originales: Kistler et al., Virtual Skeleton Database (SICAS Medical Image Repository), con aprobación del Comité de Ética del Cantón de Berna.

Cualquier malla, imagen o resultado derivado de esos datos se comparte con la misma licencia y **solo para uso no comercial**. Este repositorio no incluye los datos originales ni las mallas derivadas: se descargan y se regeneran con los scripts.

## Datos de resonancia (carpeta 01 y 04)

El caso MRBrainTumor1 es un dato de ejemplo distribuido con 3D Slicer (https://github.com/Slicer/SlicerTestingData). No se incluye en este repositorio; se descarga desde el módulo SampleData. Los modelos de impresión de la carpeta 01 se derivan de él.

## Software de terceros

3D Slicer, Blender, OrcaSlicer, VTK, SciPy, NumPy, Pillow, three.js, docx (npm) y ffmpeg se usan bajo sus propias licencias. El archivo `Craniotomy_Trainer_Quest3.html` incluye three.js (licencia MIT) empaquetado.

## Uso clínico

Nada de lo que contiene este repositorio es un dispositivo médico. No debe usarse para diagnosticar, planificar ni realizar tratamientos en personas.
