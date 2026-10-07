# LinkedIn post · English

**From an MRI to a craniotomy you can rehearse in mixed reality 🧠🥽**

What does it take to turn a brain MRI into something a surgical team could practice on? I built the full chain, open-source and end to end, as an academic exercise:

🔹 **Segmentation (3D Slicer):** seed strokes + Grow from seeds isolated a frontal, contrast-enhancing mass next to the midline: **16.9 cm³, 39.8 mm** maximum diameter.
🔹 **Tissue analysis:** the lesion enhances **~2× more than white matter** and is markedly more heterogeneous (coefficient of variation 13 % vs 5 %).
🔹 **Planning:** shortest path to the scalp, kept ≥ 15 mm from the midline to spare the superior sagittal sinus. Craniotomy window ≈ 54 mm (tumor + 10 mm margin).
🔹 **Patient-specific template:** a 3 mm scalp-fitting guide, a flat-based fit-test phantom and a 1:1 tumor model, sliced for a desktop printer (template ≈ 1 h 45 min).
🔹 **Mixed-reality trainer (Meta Quest 3, WebXR):** fit the template, mark the outline, lift the bone flap, open the dura and watch the brain shift (4.4 mm literature mean), then resect the tumor voxel by voxel, scored on residual tumor and healthy tissue removed.

The detail I like most: the simulator shows why a plan that is perfect on the MRI can be 4–5 mm off once the dura is open.

⚠️ Academic exercise with public sample data (3D Slicer MRBrainTumor1). Not a medical device, not for clinical use. The skull is approximated and tissue mechanics are simplified.

Tools: 3D Slicer · Python · Blender · OrcaSlicer · three.js/WebXR

If you work at the intersection of biomedical engineering, surgical planning or XR, I'd love to compare notes. Follow me for the next build in this series 👇

#BiomedicalEngineering #Neurosurgery #3DSlicer #MixedReality #MetaQuest #3DPrinting #MedicalImaging #SurgicalPlanning #WebXR #MedTech

---

# Publicación de LinkedIn · Español

**De una resonancia magnética a una craneotomía que se puede ensayar en realidad mixta 🧠🥽**

¿Qué hace falta para convertir una resonancia cerebral en algo con lo que un equipo quirúrgico pueda practicar? Construí la cadena completa, de principio a fin y con software abierto, como ejercicio académico:

🔹 **Segmentación (3D Slicer):** con trazos de semilla y Grow from seeds aislé una masa frontal que realza con contraste, junto a la línea media: **16,9 cm³** y **39,8 mm** de diámetro máximo.
🔹 **Análisis del tejido:** la lesión realza **unas 2 veces más que la sustancia blanca** y es bastante más heterogénea (coeficiente de variación del 13 % frente al 5 %).
🔹 **Planificación:** trayecto más corto hasta el cuero cabelludo, a ≥ 15 mm de la línea media para respetar el seno sagital superior. Ventana de craneotomía de unos 54 mm (tumor + 10 mm de margen).
🔹 **Plantilla a medida:** guía de 3 mm que se adapta al cuero cabelludo, un maniquí de prueba con base plana y un modelo del tumor 1:1, laminados para una impresora de escritorio (plantilla ≈ 1 h 45 min).
🔹 **Simulador de realidad mixta (Meta Quest 3, WebXR):** ajustar la plantilla, marcar el contorno, levantar el colgajo óseo, abrir la duramadre y ver el desplazamiento cerebral (4,4 mm de media en la literatura), y resecar el tumor vóxel a vóxel con puntuación de tumor residual y tejido sano retirado.

El detalle que más me gusta: el simulador muestra por qué un plan perfecto en la resonancia puede quedar a 4–5 mm de la realidad al abrir la duramadre.

⚠️ Ejercicio académico con datos públicos de ejemplo (3D Slicer MRBrainTumor1). No es un dispositivo médico ni apto para uso clínico. El cráneo es aproximado y la mecánica de los tejidos está simplificada.

Herramientas: 3D Slicer · Python · Blender · OrcaSlicer · three.js/WebXR

Si trabajas en ingeniería biomédica, planificación quirúrgica o realidad extendida, me encantaría intercambiar ideas. Sígueme para el próximo proyecto de esta serie 👇

#IngenieríaBiomédica #Neurocirugía #3DSlicer #RealidadMixta #MetaQuest #Impresión3D #ImagenMédica #PlanificaciónQuirúrgica #WebXR #MedTech

---

## Consejos para publicar
- Acompaña el texto con `brain_tumor_60s_EN.mp4` (o con una foto de la plantilla impresa sobre el maniquí cuando la tengas).
- Publica entre semana por la mañana y responde a los primeros comentarios: eso ayuda al alcance.
- Si lo grabas con las Quest 3 puestas, ese clip suele llamar más la atención que la pantalla del PC.
