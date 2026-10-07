# Texto para redes sociales — Análisis de elementos finitos de un fémur

## Versión sencilla (para todo público)

🦴 ¿Cuánto peso aguanta un hueso del muslo?

Con una tomografía y un programa de computadora armamos un fémur en 3D y simulamos qué pasa cuando lo apretamos con 100 N, que es como ponerle encima un peso de unos 10 kilos.

✅ Resultado: casi ni se nota. El hueso se hunde menos que el grosor de un cabello (0,1 mm) y trabaja muy por debajo de su límite.

¿Y cuándo se rompe?
• Al caminar, la cadera soporta de 2 a 3 veces tu peso; al correr, hasta unas 5 veces.
• Un fémur sano necesita una fuerza enorme para romperse: varios miles de newtons, como cargar cientos de kilos.
• Pero un hueso debilitado por la edad (osteoporosis) puede fracturarse con una simple caída de costado.
• Además, el hueso aguanta mejor los empujones de frente que los golpes de lado o las torceduras.

Esta técnica se llama "análisis de elementos finitos". Se usa para diseñar prótesis, planear cirugías e imprimir piezas en 3D.

⚠️ Es una simulación simplificada y no sirve para diagnosticar a nadie.

#Huesos #Ingeniería #Biomecánica #Salud #3D

---

## Guion para video de 30 segundos (tono divertido)

**Escena 1 (0–5 s) — los fémures girando**
"¿Cuánto peso aguanta tu hueso más grande? 🦴 Lo probamos… en computadora."

**Escena 2 (5–12 s) — la malla de elementos finitos**
"Con una tomografía armamos este fémur en 3D y lo dividimos en miles de piececitas. Eso se llama elementos finitos."

**Escena 3 (12–19 s) — apoyo azul y flecha roja**
"Lo apoyamos abajo y le pusimos encima 100 newtons. Es como un paquete de 10 kilos sobre la cadera."

**Escena 4 (19–25 s) — colores de tensión**
"¿Resultado? Casi todo azul: el hueso ni sudó. Se hunde menos que un cabello."

**Escena 5 (25–30 s) — cierre**
"Para romperlo hacen falta cientos de kilos… o una caída mala si el hueso está débil. Cuida tus huesos 💪"

**Texto de la publicación:**
¿Cuánto aguanta un fémur? Simulamos 10 kilos de peso y el hueso ni se enteró 🦴😎 Es una simulación simplificada, no sirve para diagnosticar. #Huesos #Ingeniería #Ciencia #3D

---

## Versión larga (LinkedIn / Facebook / Instagram)

🦴 ¿Cuánta fuerza aguanta un fémur… y cuándo se rompe?

Tomamos la tomografía (CT) de un cuerpo donador, extrajimos el fémur en 3D Slicer y le aplicamos un análisis de elementos finitos (FEA): dividimos el hueso en ~51 000 tetraedros, fijamos los cóndilos y cargamos la cabeza femoral con 100 N de compresión.

📊 Resultado con 100 N
• Tensión de von Mises media: ~0,36 MPa
• Desplazamiento máximo: ~0,1 mm
• Sección media: ~0,25 MPa, que coincide con el cálculo teórico F/A (verificación básica del modelo)

¿Y eso qué significa? 100 N es una carga pequeña (≈10 kg). Según la literatura, el hueso cortical sano resiste del orden de 130–200 MPa a compresión, así que aquí trabaja muy por debajo de su límite.

⚠️ ¿Cuándo se rompe un fémur?
• Caminar genera en la cadera fuerzas de ~2–3 veces el peso corporal; correr, hasta ~5 veces.
• Un fémur proximal sano suele fracturarse en ensayos con varios kN (del orden de 4–10 kN según edad y dirección de la carga).
• En personas mayores con osteoporosis, una caída lateral (~2–4 kN) puede bastar para fracturar el cuello femoral.
• El hueso resiste mejor la compresión que la flexión o la torsión: por eso las fracturas suelen ocurrir por cargas "de costado" o por impactos.

🧪 Lo que el modelo NO dice
Este análisis es lineal y estático, trata el hueso como sólido homogéneo (sin hueso esponjoso ni canal medular) y usa un solo caso de carga. No predice fracturas ni sirve para decisiones clínicas. Los picos locales de tensión dependen de la malla y no están convergidos. El CT es de una persona de 95 años, con hueso de baja densidad, así que no representa a un adulto joven.

💡 Para qué sirve este tipo de análisis: diseño de prótesis e implantes, guías quirúrgicas, estudio de osteoporosis y planificación de impresión 3D biomédica.

Flujo: CT → segmentación → malla 3D → elementos finitos → visualización, todo con software abierto (3D Slicer + Python).

Datos: VSDFullBody / Fischer, M.C.M., Sci Data 10, 763 (2023), licencia CC BY-NC-SA 4.0 (uso no comercial).

#Biomecánica #ElementosFinitos #FEA #3DSlicer #IngenieríaBiomédica #Fémur #Ortopedia #ImpresiónMédica3D #Osteoporosis #Ingeniería

---

## Versión corta (X / Twitter / Reels)

🦴 Simulamos 100 N de compresión sobre un fémur real (CT → 3D Slicer → elementos finitos).
Resultado: ~0,36 MPa de tensión media y ~0,1 mm de desplazamiento, muy lejos de los ~130–200 MPa que aguanta el hueso cortical sano.
Un fémur sano suele romperse con varios kN, y el de una persona mayor puede fracturarse en una caída lateral.
Ojo: modelo simplificado, no clínico. 🎥👇
#Biomecánica #FEA #3DSlicer

---

## Notas para quien publica
- Las cifras de la literatura (resistencia del hueso cortical, fuerzas en la cadera, cargas de fractura) son rangos aproximados. Conviene verificar la fuente antes de publicar, porque varían mucho con la edad, el sexo, la densidad ósea y el método de ensayo.
- Lo calculado en este proyecto: 100 N, E = 17 GPa, ν = 0,3, apoyo fijo en los 4 mm inferiores de los cóndilos, malla de ~51 000 tetraedros (fémur izquierdo).
- Los datos del CT tienen licencia CC BY-NC-SA: publicar con crédito y sin fines comerciales.
- Video sugerido: `femur_slicer_FEA_pantalla.mp4` (interfaz real de Slicer) o `femur_slicer_FEA.mp4` (solo vista 3D con subtítulos).
