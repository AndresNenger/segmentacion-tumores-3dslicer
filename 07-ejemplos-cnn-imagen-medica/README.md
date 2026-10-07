# Ejemplos de CNN para imagen médica

Recursos para pasar de la segmentación manual con 3D Slicer a la segmentación con redes neuronales convolucionales (CNN).

> Material educativo. Un modelo entrenado con datos de ejemplo no es un dispositivo médico ni sirve para diagnosticar.

## 1. Ejemplo propio y probado: `unet2d_sintetico.py`

Una U-Net 2D de unos 117 000 parámetros que aprende a segmentar manchas redondas en imágenes sintéticas. No descarga nada.

```bash
pip install torch numpy
python unet2d_sintetico.py
```

En una CPU tarda unos 20 segundos y llega a un Dice de ≈ 0,999 en imágenes que no vio. **Ese número es alto porque el problema sintético es fácil**: sirve para entender el flujo (datos → red → pérdida → Dice), no para esperar ese resultado con imágenes reales.

Qué enseña, en el código:
- una U-Net con **conexiones de salto** (cada nivel del decodificador recibe el mapa del nivel equivalente del codificador);
- una pérdida combinada **BCE + Dice**, habitual cuando la lesión ocupa una parte pequeña de la imagen;
- cómo medir el **coeficiente de Dice** en un conjunto de validación separado.

Probado con Python 3.12 y PyTorch 2.14 (CPU).

## 2. Recursos externos recomendados

Abrí cada enlace para confirmar qué contiene; no ejecuté su código.

| Recurso | Qué es | Para qué sirve |
|---|---|---|
| [Project-MONAI/tutorials](https://github.com/Project-MONAI/tutorials) | Tutoriales oficiales de MONAI (marco de PyTorch para imagen médica). Incluye carpetas de segmentación 2D y 3D con U-Net sobre datos sintéticos, y se pueden ejecutar en Colab. | El mejor punto de partida para pasar de 2D a 3D con volúmenes médicos. |
| [MIC-DKFZ/nnUNet](https://github.com/MIC-DKFZ/nnUNet) | Marco de segmentación "autoconfigurable": analiza tu conjunto de datos y elige solo el preprocesado, la U-Net y el entrenamiento. | La línea base a batir en segmentación 3D; no hace falta ser experto. [Artículo en Nature Methods](https://www.nature.com/articles/s41592-020-01008-z). |
| [MedMNIST](https://github.com/MedMNIST/MedMNIST) | 18 conjuntos de imágenes biomédicas 2D y 3D, ya reducidas a 28 × 28 (o 28 × 28 × 28) y listos para `pip install medmnist`. [Artículo](https://www.nature.com/articles/s41597-022-01721-8). | Practicar **clasificación** con CNN en minutos, sin GPU ni datos pesados. |

## 3. Ruta sugerida para quien viene de 3D Slicer

1. Corre `unet2d_sintetico.py` y cambia el tamaño de la red o la pérdida para ver qué pasa.
2. Prueba MedMNIST para clasificación.
3. Sigue un tutorial 2D y luego uno 3D de MONAI.
4. Con tus propias segmentaciones de 3D Slicer (los `.seg.nrrd` de este repositorio son un ejemplo del formato), prueba nnU-Net; necesita decenas de casos, no uno solo.

## Límites

- Un solo caso, como el de este repositorio, **no alcanza** para entrenar una CNN: hacen falta decenas o cientos de volúmenes segmentados.
- No comprobé las licencias de los conjuntos de datos que usan esos proyectos; revísalas antes de reutilizarlos.
