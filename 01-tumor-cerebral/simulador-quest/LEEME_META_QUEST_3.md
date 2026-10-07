# Craniotomy Trainer XR · cómo usarlo en Meta Quest 3

> Ejercicio académico con el dato de ejemplo MRBrainTumor1 de 3D Slicer. No es un dispositivo médico ni sirve para uso clínico.

## Qué incluye
- `index.html`: el simulador (three.js + WebXR). Funciona en VR, en realidad mixta (passthrough) y en el navegador del PC.
- `vr_escena_tumor.glb`: escena a escala 1:1 (cuero cabelludo, cráneo aproximado, colgajo óseo, tumor, plantilla, contorno y trayectoria). También se puede abrir en otras apps de Quest que lean GLB.
- `vr_data.json`: vóxeles de tumor (4 103) y de tejido sano (anillo de 3 mm), contorno planificado y parámetros.
- `servidor_quest.py` + `cert.pem` / `key.pem`: servidor HTTPS local. WebXR exige HTTPS.

## Opción A · Wi-Fi (recomendada)
1. El PC y las Quest 3 deben estar en la **misma red Wi-Fi**.
2. En el PC, ejecuta el servidor:
   `"C:\Users\Laboratorio\AppData\Local\slicer.org\3D Slicer 5.12.4\bin\PythonSlicer.exe" servidor_quest.py`
   (desde esta carpeta). Si Windows pregunta por el firewall, permite el acceso en **redes privadas**.
3. En las Quest, abre el **Meta Quest Browser** y entra en la dirección que imprime el servidor, por ejemplo `https://192.168.100.13:8443/index.html`.
4. El certificado es autofirmado: elige **Avanzado → Continuar**.
5. Pulsa **Enter VR** (realidad virtual) o **Enter passthrough** (realidad mixta, ves tu habitación).

## Opción B · cable USB (si la Wi-Fi o el firewall bloquean)
Con el modo desarrollador de las Quest activado y ADB instalado: `adb reverse tcp:8443 tcp:8443`, y en el navegador de las Quest abre `https://localhost:8443/index.html`.

## Controles
| Mando | Acción |
|---|---|
| Gatillo derecho | herramienta: marcar el contorno / resecar |
| Grip derecho | agarrar la plantilla |
| Grip izquierdo | mover toda la cabeza (para alinearla con un maniquí impreso en passthrough) |
| A / B | paso siguiente / anterior |
| X / Y | mostrar u ocultar cuero cabelludo / cráneo |
| Stick derecho ↑↓ | radio de la herramienta, o desplazamiento cerebral en el paso 4 |

## Pasos del entrenamiento
1. **View**: inspeccionar el plan (tumor de 16,9 cm³, ventana de unos 54 mm, trayectoria a ≥ 15 mm de la línea media).
2. **Fit**: colocar la plantilla; "seated" si queda a < 2 mm y < 2° de la posición planificada.
3. **Mark**: trazar el contorno de la craneotomía; se mide la desviación media y máxima y el % del contorno cubierto.
4. **Open**: levantar el colgajo óseo y abrir la duramadre; el cerebro se desplaza según el valor elegido (media de la literatura: 4,4 mm), y se ve la diferencia con el plan.
5. **Resect**: aspirar los vóxeles del tumor evitando el anillo sano; se mide el % resecado, el tumor residual, el tejido sano retirado y el tiempo. La vibración del mando cambia con el tejido (hueso más fuerte).

## Parámetros físicos y fisiológicos usados
| Parámetro | Valor del modelo | Referencia |
|---|---|---|
| Cuero cabelludo | 4,0 mm | adultos 3–5 mm |
| Hueso frontal | 7,5 mm | medias en TC ≈ 6,6–8,0 mm |
| Rigidez cerebral (elastografía por RM) | ≈ 3 kPa | — |
| Rigidez de meningioma (elastografía por RM) | 3,8 ± 1,7 kPa | rango 1,6–12,6 kPa |
| Desplazamiento cerebral tras abrir la duramadre | 4,4 mm (ajustable 0–12 mm) | media inmediata 4,4 mm; 5,6 mm a la hora |
| Presión intracraneal normal | 5–15 mmHg | — |
| Presión de perfusión cerebral (PPC = PAM − PIC) | alarma si < 60 mmHg | — |

## Limitaciones
- **No lo he probado en unas Quest 3.** Sí probé en el navegador del PC los pasos de ajuste, marcado, apertura y resección.
- **El cráneo es una aproximación** por espesores de referencia: la T1 no muestra bien el hueso.
- **No hay mecánica de tejidos validada.** La rigidez solo cambia la vibración y el aviso de acceso, y el desplazamiento cerebral es un traslado rígido del tumor.
- **La fisiología es informativa.** La PPC se calcula con los valores que eliges y no está acoplada a la cirugía.
- **El artefacto de claude.ai probablemente no permite WebXR.** Úsalo para practicar con ratón o pantalla táctil, y usa esta carpeta local para las gafas.

## Modo demostración
Abre `index.html#demo` (o el artefacto con `#demo` al final del enlace) y el simulador recorre solo los cinco pasos con subtítulos en inglés. Es el que se usó para grabar los videos.
