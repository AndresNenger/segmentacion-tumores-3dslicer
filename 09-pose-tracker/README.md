# Pose Tracker: ángulos articulares con MediaPipe

Cuaderno de Google Colab que detecta la **postura del cuerpo** en un video (o con la webcam), calcula **11 ángulos articulares** y la velocidad de la muñeca derecha, los compara con rangos de referencia y exporta un CSV, un video con el esqueleto dibujado y gráficas.

Pensado para tres usos: **fisioterapia** (rango de movimiento), **ergonomía** (posturas sostenidas) y **deporte**.

> **No es un dispositivo médico ni una herramienta de diagnóstico.** Los rangos de referencia son valores de partida **sin validación clínica**, como indica el propio cuaderno. Deben revisarlos un fisioterapeuta o un ergónomo antes de usarlos con pacientes.

**Archivo:** [`pose_tracker.ipynb`](pose_tracker.ipynb) (sin salidas; salió de un cuaderno ejecutado en Colab).

## Cómo usarlo

1. Abre el cuaderno en Colab (*Archivo → Subir cuaderno*) o con el botón de Colab desde GitHub.
2. Ejecuta las celdas en orden. Tras la celda 1 (instala `mediapipe`, `opencv-python`, `pandas`, `matplotlib`), reinicia el entorno si es la primera vez.
3. Elige el enfoque en la configuración: `ENFOQUE = "fisioterapia"` (o `"ergonomia"`, `"deporte"`).
4. Elige la fuente en la sección 9:
   - **Opción A:** sube un video (`sesion.mp4`) al panel de archivos de Colab y ejecuta `procesar("sesion.mp4")`.
   - **Opción B:** graba con tu webcam desde el navegador (`grabar_desde_navegador(segundos=30)`); el navegador pide permiso para la cámara.
5. Descarga el CSV y mira el video anotado y las gráficas.

El modelo (`pose_landmarker_full.task`, unos 9 MB) se descarga solo desde `storage.googleapis.com/mediapipe-models/`. Con la variable `MODEL_VARIANT` puedes elegir `lite` (rápido), `full` o `heavy` (más preciso).

## Qué mide

| Ángulos (en el vértice) | Articulaciones |
|---|---|
| Codo, hombro, cadera, rodilla, tobillo | izquierda y derecha (10 ángulos) |
| Cuello | hombro izquierdo – nariz – hombro derecho (1 ángulo) |

Además registra la **velocidad de la muñeca derecha** en píxeles por segundo (promedio de una ventana de 5 cuadros).

**CSV de salida:** una fila por cuadro con `timestamp`, `t_s`, `enfoque`, `fps`, `velocidad_muneca_der_px_s`, cada ángulo y, para cada uno, su estado `*_estado`: `ok`, `alerta` (hasta un 15 % fuera del rango), `fuera_rango` o `sin_dato`.

## Límites que conviene conocer

- **Los ángulos son 2D.** Se calculan con las coordenadas de la imagen, así que dependen de dónde esté la cámara: una persona de perfil o de frente da ángulos distintos para el mismo movimiento.
- **La velocidad está en píxeles, no en metros.** Cambia con la distancia a la cámara; no se puede comparar entre videos sin calibrar.
- **Los rangos de referencia no están validados.** En la gráfica de una ejecución con una persona de pie, la cadera y la rodilla (≈ 175-180°) salieron en *alerta* porque superan el máximo del rango de fisioterapia (170° y 175°), y el cuello y los tobillos quedaron fuera de rango por cómo está definido su ángulo. Es decir, **estar de pie y relajado puede marcarse como alerta**: interpreta el semáforo con criterio.
- Una sola persona por video (`num_poses=1`).
- Solo se registra a una persona si el modelo la detecta con confianza (`CONFIANZA = 0.6`); si no, la fila no se escribe.
- Probado por quien lo ejecutó en Colab (hay una ejecución de 13 s). **No lo volví a ejecutar** para este repositorio.

## Privacidad

Un video con una persona es un dato personal. Antes de grabar o subir videos de pacientes, estudiantes u otras personas, pide su **consentimiento**. Este repositorio **no incluye videos ni CSV** de nadie, y el cuaderno se subió sin salidas.

## Licencias

- Código del cuaderno: MIT (ver la licencia del repositorio).
- MediaPipe y sus modelos: licencia de Google/MediaPipe; consulta sus condiciones de uso antes de redistribuir el modelo.

## Siguiente paso

El propio cuaderno prevé subir el CSV a un *dashboard* para cambiar de enfoque sin recapturar. Ese dashboard no forma parte de este repositorio.
