# Social media text · Texto para redes sociales

## 🇬🇧 English

**From a CT scan to a 3D-printed surgical guide 🦴🖨️**

This academic project shows how engineering and biomedicine work together. Starting from a real CT scan (a cadaver dataset), we built a concept for a guide that helps orient the cup of a hip prosthesis.

**What we did, step by step**
1️⃣ **Segmentation:** we separated the pelvis bones from the CT in 3D Slicer.
2️⃣ **3D models:** we cleaned them into closed, printable meshes.
3️⃣ **Finite element analysis:** we simulated how the hip bone carries a load, using cortical bone properties.
4️⃣ **Planning:** we defined the cup axis (40° inclination, 15° anteversion, 48 mm cup).
5️⃣ **Guide design:** 3 contact patches that copy the bone surface + a tube aligned with the cup axis.
6️⃣ **3D print preparation:** orientation, supports and a bone replica to test the fit on a physical model (≈ 2 h print on a desktop printer).

**What the simulation showed**
In an extreme 200 kN case (far above normal hip loads of ~2–6 kN) almost half of the bone volume exceeds the strength of cortical bone, so the bone would fail. It is a way to see where the stress concentrates, not a prediction for a real patient.

⚠️ **Important:** this is an academic exercise with cadaver data. It is NOT a medical device and must NOT be used in patients. A real surgical guide needs patient-specific imaging, a surgeon's plan, validation and regulatory approval (FDA, EU MDR, ARCSA in Ecuador, etc.).

Data: Fischer, Sci Data 2023 (CC BY-NC-SA). Tools: 3D Slicer, Python, OrcaSlicer.

What would you like us to simulate next? 👇

#BiomedicalEngineering #Biomechanics #3DPrinting #3DSlicer #FiniteElementAnalysis #Orthopedics #MedTech #STEM #Engineering #Innovation

---

## 🇪🇸 Español

**De una tomografía a una guía quirúrgica impresa en 3D 🦴🖨️**

Este proyecto académico muestra cómo trabajan juntas la ingeniería y la biomedicina. A partir de un CT real (datos de un cadáver) construimos el concepto de una guía que ayuda a orientar la copa de una prótesis de cadera.

**Lo que hicimos, paso a paso**
1️⃣ **Segmentación:** separamos los huesos de la pelvis del CT en 3D Slicer.
2️⃣ **Modelos 3D:** los depuramos hasta tener mallas cerradas e imprimibles.
3️⃣ **Análisis por elementos finitos:** simulamos cómo el hueso coxal soporta una carga, con propiedades de hueso cortical.
4️⃣ **Planificación:** definimos el eje de la copa (40° de inclinación, 15° de anteversión, copa de 48 mm).
5️⃣ **Diseño de la guía:** 3 parches de contacto que copian la superficie del hueso + un tubo alineado con el eje de la copa.
6️⃣ **Preparación para imprimir:** orientación, soportes y una réplica ósea para probar el ajuste en un modelo físico (≈ 2 h de impresión en una impresora de escritorio).

**Qué mostró la simulación**
En un caso extremo de 200 kN (muy por encima de las cargas normales de la cadera, de unos 2–6 kN) casi la mitad del volumen del hueso supera la resistencia del hueso cortical, así que el hueso fallaría. Sirve para ver dónde se concentra la tensión, no es una predicción para un paciente real.

⚠️ **Importante:** es un ejercicio académico con datos de un cadáver. NO es un dispositivo médico y NO debe usarse en pacientes. Una guía quirúrgica real necesita imágenes del paciente, el plan de un cirujano, validación y aprobación regulatoria (FDA, MDR de la UE, ARCSA en Ecuador, etc.).

Datos: Fischer, Sci Data 2023 (CC BY-NC-SA). Herramientas: 3D Slicer, Python, OrcaSlicer.

¿Qué te gustaría que simuláramos después? 👇

#IngenieríaBiomédica #Biomecánica #ImpresiónMédica3D #3DSlicer #ElementosFinitos #Ortopedia #Ingeniería #STEM #Innovación

---

## Short versions · Versiones cortas

**EN (TikTok / X):** CT scan → 3D bone model → stress simulation → surgical-guide concept → 3D print 🤯 An academic project mixing engineering + biomedicine. Not a medical device, not for clinical use. What should we simulate next? #BiomedicalEngineering #3DPrinting #STEM

**ES (TikTok / X):** Tomografía → modelo 3D del hueso → simulación de tensiones → guía quirúrgica → impresión 3D 🤯 Un proyecto académico que une ingeniería y biomedicina. No es un dispositivo médico ni apto para uso clínico. ¿Qué simulamos después? #IngenieríaBiomédica #Impresión3D #STEM
