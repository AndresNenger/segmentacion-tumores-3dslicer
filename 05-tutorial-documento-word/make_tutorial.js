const fs = require("fs");
const path = require("path");
const D = require("docx");
const { Document, Packer, Paragraph, TextRun, ImageRun, Table, TableRow, TableCell, WidthType, ShadingType, BorderStyle, AlignmentType,
  HeadingLevel, LevelFormat, TableOfContents, Footer, Header, PageNumber, PageBreak, ExternalHyperlink } = D;

const SIZES = JSON.parse(fs.readFileSync(path.join(__dirname, "sizes.json"), "utf8"));
const IMG = path.join(__dirname, "imagenes");
const PAGE_W = 11906, PAGE_H = 16838, MARGIN = 1134, CONTENT = PAGE_W - 2 * MARGIN; // 9638 DXA
const FONT = "Calibri", MONO = "Consolas";
const C = { ink: "1F2933", muted: "5B6B79", accent: "0B7A75", line: "C9D3DB", note: "EAF4F3", warn: "FFF3DC", code: "F3F5F7", head: "0B7A75" };

let figN = 0;
const run = (t, o = {}) => new TextRun({ text: t, font: FONT, size: 22, color: C.ink, ...o });
const P = (parts, o = {}) => new Paragraph({ spacing: { after: 120, line: 300 }, ...o, children: (Array.isArray(parts) ? parts : [parts]).map((x) => (typeof x === "string" ? run(x) : x)) });
const B = (t) => run(t, { bold: true });
const I = (t) => run(t, { italics: true });
const K = (t) => run(t, { font: MONO, size: 20, shading: { type: ShadingType.CLEAR, fill: C.code, color: "auto" } });
const H1 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 360, after: 160 }, children: [new TextRun({ text: t, font: FONT, size: 34, bold: true, color: C.accent })] });
const H2 = (t) => new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 240, after: 100 }, children: [new TextRun({ text: t, font: FONT, size: 26, bold: true, color: C.ink })] });
const bullet = (parts) => new Paragraph({ numbering: { reference: "bul", level: 0 }, spacing: { after: 60, line: 290 }, children: (Array.isArray(parts) ? parts : [parts]).map((x) => (typeof x === "string" ? run(x) : x)) });
let curList = "l0"; const lists = ["l0"];
const newList = () => { curList = "l" + lists.length; lists.push(curList); return null; };
const step = (parts) => new Paragraph({ numbering: { reference: curList, level: 0 }, spacing: { after: 80, line: 290 }, children: (Array.isArray(parts) ? parts : [parts]).map((x) => (typeof x === "string" ? run(x) : x)) });
const border = { style: BorderStyle.SINGLE, size: 4, color: C.line };
const borders = { top: border, bottom: border, left: border, right: border };

function box(kind, title, lines) {
  const fill = kind === "warn" ? C.warn : C.note, bar = kind === "warn" ? "E0A030" : C.accent;
  const kids = [new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: title, font: FONT, size: 22, bold: true, color: C.ink })] })]
    .concat(lines.map((l) => new Paragraph({ spacing: { after: 50, line: 280 }, children: (Array.isArray(l) ? l : [l]).map((x) => (typeof x === "string" ? run(x, { size: 21 }) : x)) })));
  return new Table({
    width: { size: CONTENT, type: WidthType.DXA }, columnWidths: [CONTENT],
    borders: { top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE }, left: { style: BorderStyle.SINGLE, size: 24, color: bar }, insideHorizontal: { style: BorderStyle.NONE }, insideVertical: { style: BorderStyle.NONE } },
    rows: [new TableRow({ children: [new TableCell({ width: { size: CONTENT, type: WidthType.DXA }, shading: { type: ShadingType.CLEAR, fill, color: "auto" },
      borders: { top: { style: BorderStyle.NONE }, bottom: { style: BorderStyle.NONE }, right: { style: BorderStyle.NONE }, left: { style: BorderStyle.SINGLE, size: 24, color: bar } },
      margins: { top: 100, bottom: 100, left: 180, right: 140 }, children: kids })] })],
  });
}
const spacer = () => new Paragraph({ spacing: { after: 100 }, children: [] });

function code(lines) {
  const rows = lines.map((l) => new Paragraph({ spacing: { after: 0, line: 255 }, children: [new TextRun({ text: l === "" ? " " : l, font: MONO, size: 18, color: "1F2933" })] }));
  return new Table({
    width: { size: CONTENT, type: WidthType.DXA }, columnWidths: [CONTENT],
    rows: [new TableRow({ children: [new TableCell({ width: { size: CONTENT, type: WidthType.DXA }, borders, shading: { type: ShadingType.CLEAR, fill: C.code, color: "auto" }, margins: { top: 100, bottom: 100, left: 160, right: 160 }, children: rows })] })],
  });
}

function fig(file, caption, widthPx = 610) {
  figN += 1;
  const [w, h] = SIZES[file];
  const ext = file.toLowerCase().endsWith(".png") ? "png" : "jpg";
  const hp = Math.round((widthPx * h) / w);
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 120, after: 60 }, keepNext: true,
      children: [new ImageRun({ type: ext, data: fs.readFileSync(path.join(IMG, file)), transformation: { width: widthPx, height: hp }, altText: { title: "Figura " + figN, description: caption, name: file } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [new TextRun({ text: "Figura " + figN + ". ", font: FONT, size: 19, bold: true, color: C.muted }), new TextRun({ text: caption, font: FONT, size: 19, italics: true, color: C.muted })] }),
  ];
}

function table(widths, header, rows, o = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  const cell = (t, w, hd, shade) => new TableCell({ width: { size: w, type: WidthType.DXA }, borders, margins: { top: 70, bottom: 70, left: 110, right: 110 },
    shading: hd ? { type: ShadingType.CLEAR, fill: C.head, color: "auto" } : shade ? { type: ShadingType.CLEAR, fill: "F7F9FA", color: "auto" } : undefined,
    children: [new Paragraph({ spacing: { after: 0, line: 270 }, children: [new TextRun({ text: String(t), font: o.mono ? FONT : FONT, size: 20, bold: hd, color: hd ? "FFFFFF" : C.ink })] })] });
  return new Table({ width: { size: total, type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: header.map((h, i) => cell(h, widths[i], true)) })].concat(rows.map((r, ri) => new TableRow({ cantSplit: true, children: r.map((t, i) => cell(t, widths[i], false, ri % 2 === 1)) }))) });
}
const link = (t, url) => new ExternalHyperlink({ link: url, children: [new TextRun({ text: t, font: FONT, size: 22, color: "0B63C5", underline: {} })] });

const children = [];
const add = (...x) => x.flat().filter((e) => e).forEach((e) => children.push(e));

// ------------------------------------------------------------------ portada
add(
  new Paragraph({ spacing: { before: 1800, after: 120 }, children: [new TextRun({ text: "TUTORIAL PASO A PASO", font: FONT, size: 24, bold: true, color: C.accent, characterSpacing: 60 })] }),
  new Paragraph({ spacing: { after: 160 }, children: [new TextRun({ text: "Del tumor en una resonancia a una craneotomía que se practica en realidad mixta", font: FONT, size: 56, bold: true, color: C.ink })] }),
  new Paragraph({ spacing: { after: 400 }, children: [new TextRun({ text: "Segmentación en 3D Slicer, análisis de tejido, plantilla de craneotomía, impresión 3D en OrcaSlicer, simulador para Meta Quest 3 y grabación del proceso", font: FONT, size: 28, color: C.muted })] }),
  box("warn", "Ejercicio académico, no clínico", [
    "Este tutorial usa el dato de ejemplo MRBrainTumor1 de 3D Slicer. Nada de lo que se genera es un dispositivo médico, un diagnóstico ni un plan para operar a una persona. Una guía quirúrgica real necesita imágenes del paciente, un plan firmado por un cirujano, validación y aprobación regulatoria.",
  ]),
  spacer(),
  P([B("Fecha: "), "4 de octubre de 2026"]),
  P([B("Software: "), "3D Slicer 5.12.4 · Blender 5.2 · OrcaSlicer · Python (el que incluye Slicer) · navegador Edge · Meta Quest 3 (opcional)"]),
  P([B("Resultado final: "), "segmentación del tumor (16,9 cm³), plantilla impresa en unas 1 h 45 min y un simulador WebXR de cinco pasos."]),
  new Paragraph({ children: [new PageBreak()] }),
  new Paragraph({ spacing: { after: 160 }, children: [new TextRun({ text: "Contenido", font: FONT, size: 34, bold: true, color: C.accent })] }),
  new TableOfContents("Contenido", { hyperlink: true, headingStyleRange: "1-2" }),
  new Paragraph({ children: [new PageBreak()] }),
);

// ------------------------------------------------------------------ 1. visión general
add(H1("1. Qué vas a construir"),
  P("Seguirás una cadena completa, de una imagen médica a un objeto impreso y a una práctica virtual. Cada paso produce un archivo que usa el siguiente."),
  newList(),
  step([B("Datos: "), "una resonancia magnética de ejemplo con un tumor frontal."], "flow"),
  step([B("Segmentación: "), "aislar el tumor en 3D Slicer con semillas y la herramienta Grow from seeds."], "flow"),
  step([B("Análisis: "), "volumen, forma e intensidad del tumor frente a la sustancia blanca."], "flow"),
  step([B("Planificación: "), "trayectoria más corta al cuero cabelludo, lejos de la línea media, y ventana de craneotomía."], "flow"),
  step([B("Plantilla: "), "pieza de 3 mm que se apoya en el cuero cabelludo y deja la ventana libre."], "flow"),
  step([B("Impresión: "), "orientar las piezas, empaquetarlas en un 3MF y laminarlas en OrcaSlicer."], "flow"),
  step([B("Simulador: "), "escena a escala 1:1 para practicar en el navegador o en unas Meta Quest 3."], "flow"),
  step([B("Video: "), "grabar solo las ventanas de las aplicaciones y añadir subtítulos."], "flow"),
  H2("Resultados que deberías obtener"),
  table([3600, 3000, 3038], ["Medida", "Valor", "Dónde se obtiene"], [
    ["Volumen del tumor", "16,94 cm³", "Segment Statistics"],
    ["Diámetro máximo (Feret)", "39,8 mm", "Segment Statistics"],
    ["Redondez", "0,94", "Segment Statistics"],
    ["Intensidad media tumor / sustancia blanca", "179 / 91 (≈ 2,0×)", "Segment Statistics"],
    ["Profundidad piel → superficie del tumor", "22,2 mm", "Planificación"],
    ["Ventana de craneotomía", "≈ 54 mm (tumor + 10 mm)", "Planificación"],
    ["Tiempo de impresión de la plantilla (Creality K1C)", "≈ 1 h 45 min", "OrcaSlicer"],
  ]),
  spacer(),
  box("note", "Cómo leer este documento", ["Cada paso explica primero cómo hacerlo con el ratón en la interfaz y después, si existe, el script equivalente. Las capturas están en la carpeta ", [K("imagenes/"), " junto a este archivo; el Anexo B indica de dónde salió cada una."]]),
  new Paragraph({ children: [new PageBreak()] }),
);

// ------------------------------------------------------------------ 2. requisitos
add(H1("2. Antes de empezar"),
  H2("Software"),
  table([2300, 1500, 5838], ["Programa", "Versión", "Para qué se usa"], [
    ["3D Slicer", "5.12.4", "Cargar la resonancia, segmentar, medir y renderizar. Incluye Python, NumPy, SciPy y VTK."],
    ["Blender", "5.2", "Convertir las mallas STL en una escena GLB para el simulador."],
    ["OrcaSlicer", "reciente", "Laminar las piezas y estimar tiempo y material (perfil Creality K1C en este tutorial)."],
    ["Navegador Edge o Chrome", "reciente", "Probar el simulador y grabarlo."],
    ["imageio-ffmpeg", "0.6", "Trae un ffmpeg listo para grabar la ventana y unir videos (opcional)."],
    ["Meta Quest 3", "—", "Practicar en VR o en realidad mixta (opcional; el simulador funciona sin gafas)."],
  ]),
  spacer(),
  H2("Carpeta de trabajo"),
  P("Crea una carpeta para todo el proyecto. Los scripts de este tutorial asumen esta estructura:"),
  code(["tumor_cerebral/", "  MRBrainTumor1.nrrd            <- dato de ejemplo (paso 1)", "  *.py                           <- scripts de cada paso", "  vr_quest/                      <- simulador WebXR (paso 7)", "  orca_out/                      <- G-code de prueba (paso 6)"]),
  spacer(),
  box("warn", "Antes de empezar a grabar", ["En el paso 8 el script maximiza la ventana de Slicer y la graba durante varios minutos. Cierra WhatsApp, el correo y las pestañas personales, y no muevas el ratón ni toques el teclado mientras grabe: cualquier clic cambiaría lo que se ve."]),
);

// ------------------------------------------------------------------ 3. Paso 1
add(H1("3. Paso 1 · Obtener el dato de ejemplo"),
  P("3D Slicer trae una colección de datos de ejemplo. El tumor cerebral es MRBrainTumor1: una resonancia T1 con contraste de 256 × 256 × 112 vóxeles (0,94 × 0,94 × 1,4 mm)."),
  H2("En la interfaz"),
  newList(),
  step("Abre 3D Slicer y, en el menú de módulos, elige SampleData."),
  step([B("Pulsa el icono "), "MRBrainTumor1. Slicer descarga el archivo (unos 5 MB) y lo muestra en los cortes axial, sagital y coronal."]),
  step("Comprueba que ves una masa brillante delante, junto a la línea media."),
  ...fig("01_sampledata.jpg", "Módulo SampleData con los datos de ejemplo disponibles."),
  ...fig("02_cargado.jpg", "MRBrainTumor1 cargado: la masa que realza con contraste se ve en los tres cortes."),
  H2("Alternativa por script"),
  P("Si prefieres no depender de la interfaz, descarga el archivo y cárgalo desde Python. El checksum evita descargar un archivo corrupto."),
  code([
    "curl -L -o MRBrainTumor1.nrrd \\",
    "  https://github.com/Slicer/SlicerTestingData/releases/download/SHA256/998cb522173839c78657f4bc0ea907cea09fd04e44601f17c82ea27927937b95",
    "",
    "# en Slicer (Python):",
    "vol = slicer.util.loadVolume('MRBrainTumor1.nrrd')",
  ]),
  spacer(),
  P("Para elegir bien el punto de partida conviene mirar el volumen entero antes de segmentar. El mosaico de la Figura 3 muestra cortes axiales cada 6 mm: el tumor aparece entre los cortes 68 y 92."),
  ...fig("00_mosaico_axial.png", "Mosaico de cortes axiales (k = 20 a 104). El tumor se ve a partir del corte 68."),
  new Paragraph({ children: [new PageBreak()] }),
);

// ------------------------------------------------------------------ 4. Paso 2
add(H1("4. Paso 2 · Segmentar el tumor con semillas"),
  P("En vez de pintar el tumor corte a corte, se marcan unas pocas semillas dentro del tumor y otras en el tejido de alrededor. La herramienta Grow from seeds hace crecer ambas regiones en 3D hasta que se encuentran en el borde del tumor. Es el método del tutorial de PerkLab que sirvió de referencia."),
  H2("En la interfaz"),
  newList(),
  step([B("Abre el módulo Segment Editor"), " y elige MRBrainTumor1 como volumen fuente."]),
  step([B("Crea dos segmentos "), "con Add: Tumor (amarillo) y Healthy tissue (azul)."], "seg"),
  ...fig("03_segment_editor.jpg", "Segment Editor con los dos segmentos creados y la herramienta Paint activa."),
  step([B("Con Tumor seleccionado, elige Paint "), "y pinta un trazo dentro del tumor en tres cortes axiales: uno en el centro y otros dos a unos 6 cortes por encima y por debajo."], "seg"),
  ...fig("04_semillas_tumor.jpg", "Semillas en el tumor (amarillo). No hace falta cubrirlo entero: bastan unos trazos bien dentro."),
  step([B("Con Healthy tissue seleccionado, "), "pinta un anillo alrededor del tumor, a 6-9 mm del borde, y un disco en un corte por encima y otro por debajo del tumor. Incluye la hoz (la línea fina en el centro) para que el tumor no se escape por ella."], "seg"),
  ...fig("05_semillas_sano.jpg", "Semillas del tejido sano (azul) rodeando el tumor."),
  step([B("Elige Grow from seeds "), "y pulsa Initialize. Revisa la vista previa en los tres cortes y, si el borde es correcto, pulsa Apply."], "seg"),
  ...fig("06_grow_preview.jpg", "Vista previa de Grow from seeds: el tumor (amarillo) y el tejido sano (azul) crecen hasta tocarse."),
  ...fig("07_grow_aplicado.jpg", "Grow from seeds aplicado: el tumor queda etiquetado en todos los cortes."),
  step([B("Limpia el resultado: "), "con Tumor seleccionado, aplica Smoothing (método Median, 3 mm) y después Islands con Keep largest island."], "seg"),
  ...fig("08_suavizado.jpg", "Suavizado mediano de 3 mm: desaparecen las puntas y los vóxeles aislados."),
  H2("Qué hace falta saber"),
  bullet([B("Un umbral simple no basta. "), "Un umbral de intensidad sigue la hoz y los vasos, que también realzan, y arrastra media cabeza. Las semillas del tejido sano son lo que frena esa fuga."]),
  bullet([B("Dos segmentos como mínimo. "), "Grow from seeds necesita semillas de al menos dos clases."]),
  bullet([B("Después puedes borrar Healthy tissue. "), "Sirvió solo para guiar el crecimiento."]),
  ...fig("24_segmentacion_cortes.png", "Contorno del tumor (amarillo) en ocho cortes axiales consecutivos tras la limpieza.", 640),
  H2("El mismo flujo por script"),
  P("Para repetirlo sin ratón, el script crea los segmentos, escribe las semillas en ellos y llama a las herramientas del Segment Editor. Las semillas se generan a partir de una estimación del tumor (umbral relativo al núcleo más una componente conectada), así que el resultado es semiautomático."),
  code([
    "seg = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode', 'Segmentation')",
    "seg.CreateDefaultDisplayNodes()",
    "seg.SetReferenceImageGeometryParameterFromVolumeNode(vol)",
    "tid = seg.GetSegmentation().AddEmptySegment('Tumor', 'Tumor')",
    "bid = seg.GetSegmentation().AddEmptySegment('Healthy', 'Healthy tissue')",
    "slicer.util.updateSegmentBinaryLabelmapFromArray(mask_tumor, seg, tid, vol)   # semillas",
    "slicer.util.updateSegmentBinaryLabelmapFromArray(mask_sano,  seg, bid, vol)",
    "",
    "w = slicer.qMRMLSegmentEditorWidget(); w.setMRMLScene(slicer.mrmlScene)",
    "w.setMRMLSegmentEditorNode(slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentEditorNode'))",
    "w.setSegmentationNode(seg); w.setSourceVolumeNode(vol)",
    "w.setActiveEffectByName('Grow from seeds'); e = w.activeEffect()",
    "e.self().onPreview(); e.self().onApply()",
    "w.setCurrentSegmentID(tid)",
    "w.setActiveEffectByName('Smoothing'); e = w.activeEffect()",
    "e.setParameter('SmoothingMethod', 'MEDIAN'); e.setParameter('KernelSizeMm', 3.0); e.self().onApply()",
    "w.setActiveEffectByName('Islands'); e = w.activeEffect()",
    "e.setParameter('Operation', 'KEEP_LARGEST_ISLAND'); e.self().onApply()",
  ]),
  spacer(),
  box("warn", "Ejecuta este script con la ventana de Slicer abierta", ["Grow from seeds se cerró de forma inesperada al ejecutarlo con --no-main-window (sin ventana). Lanza Slicer normal con --python-script y la interfaz visible."]),
  new Paragraph({ children: [new PageBreak()] }),
);

// ------------------------------------------------------------------ 5. Paso 3
add(H1("5. Paso 3 · Medir el tumor y analizar el tejido"),
  H2("Volumen, forma e intensidad"),
  newList(),
  step("Abre el módulo Segment Statistics."),
  step("Elige la segmentación y MRBrainTumor1 como volumen escalar."),
  step([B("Activa "), "Labelmap statistics (volumen, diámetro de Feret, redondez, superficie) y Scalar volume statistics (media, desviación, percentiles)."]),
  step("Pulsa Apply."),
  ...fig("10_estadisticas.jpg", "Segment Statistics con las medidas del tumor y de la región de referencia."),
  H2("Comparar con la sustancia blanca"),
  P("Para saber cuánto realza el tumor hace falta una referencia. Crea un tercer segmento con una esfera de 6 mm (0,93 cm³) en sustancia blanca homogénea del hemisferio contrario: el script busca el punto con menor desviación local de intensidad dentro de la zona profunda."),
  table([3300, 2000, 2000, 2338], ["Medida", "Tumor", "Sustancia blanca", "Nota"], [
    ["Volumen", "16,94 cm³", "0,93 cm³", "la referencia es una esfera de 6 mm"],
    ["Intensidad media", "179", "91", "el tumor realza ≈ 2,0×"],
    ["Desviación estándar", "24", "4,4", ""],
    ["Coeficiente de variación", "13 %", "4,8 %", "el tumor es más heterogéneo"],
    ["Diámetro máximo (Feret)", "39,8 mm", "—", ""],
    ["Redondez", "0,94", "—", "casi esférico"],
    ["Superficie", "3 408 mm²", "—", ""],
  ]),
  spacer(),
  ...fig("11_histograma.jpg", "Histograma de intensidades: el tumor (amarillo) está desplazado hacia valores altos y es más ancho que la sustancia blanca (verde)."),
  box("warn", "Qué NO significan estos números", ["Las intensidades de una resonancia son unidades de señal, no propiedades del tejido. El realce con contraste no permite decir qué tipo de tumor es: eso lo decide la histología."]),
  new Paragraph({ children: [new PageBreak()] }),
);

// ------------------------------------------------------------------ 6. Paso 4
add(H1("6. Paso 4 · Planificar el abordaje"),
  H2("Modelo 3D y superficie de la cabeza"),
  P("Con el tumor segmentado, genera su modelo 3D (botón Show 3D del Segment Editor) y una superficie de la cabeza a partir de la propia resonancia: umbral, cierre y relleno de huecos."),
  ...fig("09_modelo3d.jpg", "Modelo 3D del tumor dentro de la superficie de la cabeza (cuero cabelludo semitransparente)."),
  H2("Trayectoria"),
  P("El script prueba miles de direcciones desde el centro del tumor hacia fuera y se queda con la más corta que llega a la piel cumpliendo dos reglas:"),
  bullet("la entrada queda en el mismo lado que el tumor;"),
  bullet("la entrada queda a 15 mm o más de la línea media, para respetar el seno sagital superior."),
  P("Resultado: entrada paramediana izquierda, 22° respecto a la vertical, unos 38 mm del centro del tumor a la piel y 22,2 mm de la piel a la superficie del tumor."),
  ...fig("12_trayectoria.jpg", "Trayectoria elegida (línea naranja) desde el cuero cabelludo hasta el centro del tumor."),
  H2("Ventana de craneotomía"),
  P("Se proyecta el tumor sobre un plano perpendicular a la trayectoria, se toma la envolvente convexa de esa silueta y se le añade un margen de 10 mm. El resultado es una ventana de unos 54 mm de diámetro máximo."),
  ...fig("13_contorno.jpg", "Contorno de la craneotomía (rojo) sobre la piel, con la trayectoria y el tumor."),
  box("note", "Parámetros del plan", [[B("Margen: "), "10 mm.  ", B("Distancia mínima a la línea media: "), "15 mm.  ", B("Apoyo de la plantilla alrededor de la ventana: "), "22 mm."]]),
  new Paragraph({ children: [new PageBreak()] }),
);

// ------------------------------------------------------------------ 7. Paso 5
add(H1("7. Paso 5 · Diseñar la plantilla de craneotomía"),
  P("La plantilla es una carcasa de 3 mm que copia el cuero cabelludo alrededor de la ventana. Se construye en una rejilla de vóxeles (0,6 mm) y se convierte a malla."),
  newList(),
  step("Dibuja la superficie de la piel como distancia con signo y suavízala con un filtro paso bajo (sigma = 3 mm). Así la plantilla no copia surcos ni objetos pegados al cuero cabelludo."),
  step("Selecciona los vóxeles de la capa entre 0,3 y 3,3 mm por fuera de la piel (0,3 mm de holgura + 3 mm de espesor)."),
  step("Quédate con la parte que cae dentro del anillo de apoyo (22 mm) y fuera de la ventana."),
  step("Conserva solo la componente conexa mayor y conviértela a malla con marching cubes, suavizado y limpieza."),
  step("Genera también el contorno (una banda de 1,2 mm en el borde de la ventana), un maniquí de cuero cabelludo con base plana para probar el asiento y un modelo 1:1 del tumor."),
  ...fig("14_plantilla.jpg", "La plantilla (verde azulado) apoyada sobre el cuero cabelludo, con el tumor debajo."),
  ...fig("23_resumen_vistas.png", "Cuatro vistas de la plantilla: oblicua, superior, solo el contorno sobre la piel y a lo largo de la trayectoria.", 640),
  H2("Comprobaciones que conviene hacer"),
  bullet("Cero vóxeles de la plantilla dentro de la cabeza."),
  bullet("Distancia mínima entre la ventana y la silueta del tumor: 10,0 mm."),
  bullet("Mallas cerradas, sin aristas abiertas, y espesor mínimo local de 2,4 mm (mediana 3,3 mm)."),
  box("warn", "Dos problemas reales que aparecieron", [
    [B("Surcos copiados: "), "la primera plantilla seguía un surco de la piel y un objeto externo pegado al cuero cabelludo en la resonancia. Se resolvió suavizando la superficie de la cabeza con el filtro paso bajo del paso 2."],
    [B("Ventana con entrantes: "), "usar la silueta cruda del tumor dejaba un entrante en el borde. La envolvente convexa da un contorno limpio, más realista para una craneotomía."],
  ]),
  new Paragraph({ children: [new PageBreak()] }),
);

// ------------------------------------------------------------------ 8. Paso 6
add(H1("8. Paso 6 · Preparar la impresión y laminar en OrcaSlicer"),
  H2("Orientar cada pieza"),
  P("Cada pieza se gira para imprimirse con el menor voladizo posible (caras que miran hacia abajo con más de 45°). El script prueba 700 orientaciones y se queda con la mejor; el maniquí se apoya sobre su base plana."),
  table([2300, 2400, 1500, 3438], ["Pieza", "Orientación", "Voladizo", "Nota"], [
    ["Plantilla", "de canto", "1,9 %", "espesor mediano 3,3 mm"],
    ["Maniquí de cuero cabelludo", "base sobre la cama", "0,2 %", "sirve para probar el asiento"],
    ["Modelo del tumor 1:1", "mínimo voladizo", "8,2 %", "referencia visual"],
  ]),
  spacer(),
  ...fig("15_preparar_impresion.jpg", "Las tres piezas sobre la placa de 220 × 220 mm; en rojo, las zonas con voladizo mayor de 45°."),
  H2("Empaquetar en un 3MF"),
  P("Si abres varios STL a la vez, OrcaSlicer pregunta si los carga como un solo objeto. Para evitar esa pregunta, el script mete las tres piezas en un único archivo 3MF, centradas en la cama (110, 110 mm)."),
  H2("En OrcaSlicer"),
  newList(),
  step("Abre placa_craneotomia.3mf (Archivo → Abrir proyecto)."),
  step("Comprueba la impresora (Creality K1C, boquilla 0,4 mm) y el filamento (PLA genérico)."),
  step("Activa los soportes automáticos y 3 paredes; con 20 % de relleno y capa de 0,16 mm la plantilla tarda unos 105 minutos."),
  step("Pulsa Laminar cama y revisa la vista previa antes de imprimir."),
  ...fig("16_orcaslicer.jpg", "OrcaSlicer con la plantilla, el maniquí y el modelo del tumor sobre la cama de la K1C.", 640),
  H2("Estimaciones por línea de comandos"),
  P("OrcaSlicer también lamina sin abrir la interfaz. Sirve para obtener tiempos y material de forma repetible."),
  code([
    "\"C:/Program Files/OrcaSlicer/orca-slicer.exe\" --slice 0 --outputdir orca_out \\",
    "  --load-settings \"machine_k1c.json;process_k1c.json\" \\",
    "  --load-filaments \"Creality Generic PLA @K1-all.json\" imprimir_plantilla.stl",
  ]),
  spacer(),
  table([3000, 2200, 2200, 2238], ["Pieza", "Tiempo", "Material", "Capas"], [
    ["Plantilla", "1 h 45 min", "20,9 cm³", "612"],
    ["Maniquí", "2 h 29 min", "43,4 cm³", "207"],
    ["Modelo del tumor", "41 min", "7,3 cm³", "246"],
  ]),
  spacer(),
  box("warn", "Detalles del perfil", [
    "Son estimaciones con un perfil genérico, sin calibrar. La captura de OrcaSlicer muestra el perfil de 0,08 mm que ya tenías; las estimaciones usan 0,16 mm.",
    [B("Si la línea de comandos falla "), "con el aviso sobre el desplazamiento relativo del extrusor, copia el perfil de la máquina y añade ", K("\"layer_change_gcode\": \"G92 E0\""), ". No hace falta tocar la instalación de OrcaSlicer."],
  ]),
  new Paragraph({ children: [new PageBreak()] }),
);

// ------------------------------------------------------------------ 9. Paso 7
add(H1("9. Paso 7 · Simulador de craneotomía para Meta Quest 3"),
  P("El simulador es una página web (three.js con WebXR) que se abre en el navegador del PC o en el Meta Quest Browser. Muestra la cabeza a escala 1:1 y permite ensayar la craneotomía en cinco pasos."),
  H2("7.1 · Preparar los recursos"),
  newList(),
  step([B("Cráneo aproximado y vóxeles. "), "Un script de Slicer crea el cráneo (hueso de 7,5 mm bajo 4 mm de cuero cabelludo), el colgajo óseo, los vóxeles del tumor (4 103 de 1,6 mm) y un anillo de 3 mm de tejido sano."], "sim"),
  step([B("Convertir a GLB. "), "Blender importa los STL (escala 0,001 para trabajar en metros), les asigna materiales y exporta un archivo GLB de unos 3 MB."], "sim"),
  step([B("Datos del plan. "), "Un JSON con la entrada, el objetivo, el contorno y los vóxeles, en coordenadas de glTF: (x, y, z) = (derecha, superior, −anterior) / 1000."], "sim"),
  H2("7.2 · Abrirlo en el PC"),
  P("Sirve cualquier servidor web local. Desde la carpeta vr_quest:"),
  code(["python -m http.server 8000", "# abre http://localhost:8000/index.html"]),
  spacer(),
  ...fig("17_sim_inicio.jpg", "Simulador al abrir: cabeza a escala 1:1, panel de pasos, fisiología y capas."),
  H2("7.3 · Los cinco pasos"),
  table([1700, 7938], ["Paso", "Qué se practica"], [
    ["1 · View", "Inspeccionar el plan: tumor de 16,9 cm³, ventana de unos 54 mm y trayectoria a 15 mm o más de la línea media."],
    ["2 · Fit", "Colocar la plantilla; cuenta como asentada cuando queda a menos de 2 mm y 2° de la posición planificada."],
    ["3 · Mark", "Trazar el contorno sobre el cuero cabelludo. Se miden la desviación media y máxima y el porcentaje del contorno cubierto."],
    ["4 · Open", "Levantar el colgajo óseo y abrir la duramadre. El cerebro se desplaza según el valor elegido y una silueta cian muestra dónde estaba el tumor en el plan."],
    ["5 · Resect", "Aspirar los vóxeles del tumor evitando el anillo sano. Se miden el porcentaje retirado, el tumor residual y el tiempo."],
  ]),
  spacer(),
  ...fig("18_sim_ajuste.jpg", "Paso 2: la plantilla se acerca a su posición planificada; el panel muestra el error de posición y de ángulo."),
  ...fig("19_sim_marcado.jpg", "Paso 3: el trazo sobre el cuero cabelludo se compara con el contorno planificado."),
  ...fig("20_sim_apertura.jpg", "Paso 4: colgajo óseo retirado y duramadre abierta; el tumor se ha desplazado respecto al plan."),
  ...fig("21_sim_reseccion.jpg", "Paso 5: resección vóxel a vóxel; en rosa, el anillo de tejido sano que se debe conservar."),
  ...fig("22_sim_fisiologia.jpg", "Panel de fisiología: con una presión intracraneal de 32 mmHg la presión de perfusión cae por debajo de 60 mmHg y salta la alarma."),
  H2("7.4 · Parámetros físicos y fisiológicos"),
  table([4300, 2200, 3138], ["Parámetro", "Valor del modelo", "Referencia"], [
    ["Cuero cabelludo", "4,0 mm", "adultos 3-5 mm"],
    ["Hueso frontal", "7,5 mm", "medias en TC ≈ 6,6-8,0 mm"],
    ["Rigidez cerebral (elastografía por RM)", "≈ 3 kPa", "—"],
    ["Rigidez de meningioma", "3,8 ± 1,7 kPa", "rango 1,6-12,6 kPa"],
    ["Desplazamiento cerebral tras abrir la duramadre", "4,4 mm (ajustable 0-12)", "media inmediata 4,4 mm"],
    ["Presión intracraneal normal", "5-15 mmHg", "—"],
    ["Presión de perfusión cerebral = PAM − PIC", "alarma si < 60 mmHg", "—"],
  ]),
  spacer(),
  H2("7.5 · Usarlo con las Meta Quest 3"),
  P("WebXR solo funciona en un contexto seguro, así que las gafas necesitan una dirección HTTPS. El paquete incluye un servidor HTTPS local con un certificado autofirmado."),
  newList(),
  step("Conecta el PC y las Quest a la misma red Wi-Fi."),
  step("En el PC, desde la carpeta vr_quest, ejecuta el servidor:"),
  code(["python servidor_quest.py", "# imprime algo como: https://192.168.100.13:8443/index.html"]),
  step("Si Windows pregunta por el firewall, permite el acceso en redes privadas."),
  step("En el Meta Quest Browser abre esa dirección. El navegador avisa del certificado: elige Avanzado y Continuar."),
  step("Pulsa Enter VR (realidad virtual) o Enter passthrough (realidad mixta)."),
  spacer(),
  table([2800, 6838], ["Control", "Acción"], [
    ["Gatillo derecho", "herramienta: marcar el contorno o resecar"],
    ["Grip derecho", "agarrar la plantilla"],
    ["Grip izquierdo", "mover toda la cabeza (para alinearla con un maniquí impreso en passthrough)"],
    ["A / B", "paso siguiente / anterior"],
    ["X / Y", "mostrar u ocultar el cuero cabelludo / el cráneo"],
    ["Stick derecho arriba/abajo", "radio de la herramienta, o desplazamiento cerebral en el paso 4"],
  ]),
  spacer(),
  box("warn", "Qué no se ha comprobado", [
    "El simulador se probó en el navegador del PC (ajuste, marcado, apertura y resección), no con unas Quest 3. Los controles de las gafas están programados pero sin verificar.",
    "El cráneo es una aproximación por espesores de referencia, porque una resonancia T1 no muestra bien el hueso. La rigidez de los tejidos no tiene una mecánica validada y el desplazamiento cerebral es un traslado rígido del tumor.",
  ]),
  H2("7.6 · Modo demostración"),
  P(["Abre ", K("index.html#demo"), " y el simulador recorre solo los cinco pasos con subtítulos en inglés, con una herramienta virtual que se mueve como el mando derecho. Es la versión que se usó para grabar los videos. Después de añadir ", K("#demo"), " a la dirección, recarga la página."]),
  new Paragraph({ children: [new PageBreak()] }),
);

// ------------------------------------------------------------------ 10. Paso 8
add(H1("10. Paso 8 · Grabar el proceso en video"),
  P("Los videos graban solo la ventana de cada programa, no el escritorio, y añaden subtítulos para que se entiendan sin voz."),
  H2("Qué se graba y cómo"),
  table([2600, 3600, 3438], ["Programa", "Método de captura", "Subtítulos"], [
    ["3D Slicer", "ffmpeg gdigrab por título de ventana", "Etiqueta superpuesta dentro de la ventana de Slicer"],
    ["OrcaSlicer", "gdigrab de la región de la ventana (DPI real)", "ffmpeg drawtext al montar"],
    ["Simulador en Edge", "gdigrab de pantalla completa en modo kiosco", "Subtítulos dentro de la propia página"],
  ]),
  spacer(),
  H2("Captura de la ventana de Slicer"),
  P("El script maximiza la ventana, lee su título y lanza ffmpeg. Después maneja Slicer en tiempo real: cambia de módulo, mueve la cámara y actualiza el subtítulo."),
  code([
    "ffmpeg -f gdigrab -framerate 24 -draw_mouse 0 -i title=\"3D Slicer 5.12.4\" \\",
    "  -vf scale=trunc(iw/2)*2:trunc(ih/2)*2 -c:v libx264 -preset veryfast -crf 20 -pix_fmt yuv420p salida.mp4",
  ]),
  spacer(),
  box("warn", "Aplicaciones con gráficos por GPU", ["gdigrab por título graba una ventana gris con OrcaSlicer o Blender. Con esas aplicaciones captura la región de pantalla de la ventana (GetClientRect + ClientToScreen), con el proceso declarado consciente del escalado de pantalla (SetProcessDpiAwareness); si no, las coordenadas salen más pequeñas que los píxeles reales y la captura recorta la ventana."]),
  H2("Montaje y subtítulos"),
  bullet("Une los tramos con el filtro concat, escalando todos a 1920 × 990 y 24 fps."),
  bullet("Los subtítulos de OrcaSlicer se incrustan con drawtext, leyendo el texto de archivos UTF-8 con la opción expansion=none (si no, el símbolo % da error)."),
  bullet("El resumen de 60 s se monta cortando fragmentos de cada escena del video completo."),
  code([
    "ffmpeg -i tramo1.mp4 -i tramo2.mp4 -i tramo3.mp4 -filter_complex_script grafo.txt \\",
    "  -map \"[v]\" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p video_completo.mp4",
  ]),
  spacer(),
  box("note", "Una buena práctica", ["Antes de dar un video por bueno, extrae una hoja de contactos (un fotograma cada pocos segundos) y compruébala: así se detectan escenas vacías, subtítulos tapados o la cámara girada."]),
  new Paragraph({ children: [new PageBreak()] }),
);

// ------------------------------------------------------------------ 11. regulatorio
add(H1("11. Limitaciones y marco regulatorio"),
  H2("Limitaciones de este trabajo"),
  bullet("Un solo caso de ejemplo; la segmentación no se comparó con una referencia experta."),
  bullet("Las semillas se generan por script: la segmentación es semiautomática, no manual."),
  bullet("La plantilla se apoya en el cuero cabelludo, que se mueve; una guía real se apoyaría en hueso y se validaría con neuronavegación."),
  bullet("No se modelan vasos, áreas elocuentes ni la mecánica real del cerebro."),
  H2("Marco regulatorio (resumen orientativo)"),
  P("Lo que sigue es un resumen educativo, no asesoría legal. Verifica siempre con un especialista en asuntos regulatorios."),
  table([2400, 7238], ["Región", "Qué conviene saber"], [
    ["Estados Unidos (FDA)", "Las guías quirúrgicas impresas en 3D suelen ser dispositivos de clase II, con notificación 510(k). La excepción para dispositivos a medida es muy restringida."],
    ["Unión Europea (MDR 2017/745)", "Se distingue «a medida» (Anexo XIII, con prescripción escrita) de «ajustado al paciente» (producción en lote bajo responsabilidad del fabricante, con evaluación de conformidad completa)."],
    ["Ecuador (ARCSA)", "El registro sanitario es obligatorio para fabricar, importar o comercializar dispositivos médicos de uso humano; existe una norma sustitutiva de 2026 (ARCSA-DE-2026-003-DASP)."],
  ]),
  spacer(),
  P("Antes de usar algo así en pacientes se exige, normalmente: un sistema de calidad (ISO 13485) y gestión de riesgos (ISO 14971), biocompatibilidad del material (serie ISO 10993) y esterilización validada, validación del proceso de impresión y del software de planificación (IEC 62304), verificación y validación del diseño, y vigilancia posterior a la comercialización. Esas normas se citan como referencia habitual."),
);

// ------------------------------------------------------------------ 12. problemas
add(H1("12. Solución de problemas"),
  table([3400, 6238], ["Síntoma", "Causa y solución"], [
    ["Grow from seeds cierra Slicer", "Ocurre en modo sin ventana. Ejecuta el script con la interfaz de Slicer abierta."],
    ["El tumor se escapa por la hoz", "Falta tejido sano marcado alrededor y sobre la hoz. Añade semillas del segmento Healthy tissue en esa línea."],
    ["La plantilla copia surcos o un objeto pegado a la piel", "Suaviza la superficie de la cabeza con la distancia con signo y un filtro paso bajo de 3 mm."],
    ["Los STL se cargan girados 180° en Slicer", "Slicer asume coordenadas LPS en los STL sin información. Cárgalos con la opción coordinateSystem = RAS."],
    ["La órbita de la cámara se tambalea", "La vista elevada hace que girar sobre el vector «arriba» de la cámara oscile. Rota la posición alrededor del eje Z vertical y fija el vector arriba."],
    ["La vista 3D sale vacía los primeros segundos", "El rango de recorte de la cámara se calculó antes de mostrar los modelos. Recalcúlalo en cada fotograma."],
    ["OrcaSlicer pregunta si carga como un solo objeto", "Empaqueta las piezas en un 3MF."],
    ["El video de OrcaSlicer sale gris o recortado", "Captura la región de la ventana y declara el proceso consciente del escalado de pantalla."],
    ["El navegador ofrece traducir la página", "Añade translate=\"no\" a la etiqueta html y lanza Edge con el idioma en inglés y la traducción desactivada."],
    ["La Quest no abre el simulador", "WebXR exige HTTPS: usa servidor_quest.py y acepta el aviso del certificado. PC y gafas deben estar en la misma red."],
  ]),
  new Paragraph({ children: [new PageBreak()] }),
);

// ------------------------------------------------------------------ anexos
add(H1("Anexo A · Archivos y scripts"),
  table([3300, 6338], ["Archivo", "Contenido"], [
    ["t1_explora.py", "Localiza el tumor y estima su volumen con umbrales relativos."],
    ["seeds.py y t2_seg.py", "Generan las semillas y ejecutan Grow from seeds, suavizado e islas; calculan las estadísticas."],
    ["t3_plan.py", "Trayectoria, ventana de craneotomía, plantilla, contorno, maniquí y modelo del tumor (STL)."],
    ["t4_render.py", "Vistas de la plantilla con la herramienta de captura de Slicer."],
    ["t5_impresion.py", "Orientación de impresión, comprobaciones y archivo placa_craneotomia.3mf."],
    ["t6_vr_assets.py y t7_glb.py", "Cráneo aproximado, colgajo, vóxeles y exportación a GLB con Blender."],
    ["vr_quest/index.html y servidor_quest.py", "Simulador WebXR y servidor HTTPS local."],
    ["video_tumor.py, video_cards_t.py, rec_orca_t.py, rec_sim.py", "Grabación de cada tramo."],
    ["informe_tumor_cerebral.md", "Resumen técnico del análisis y de sus limitaciones."],
  ]),
  spacer(),
  H1("Anexo B · Origen de las capturas"),
  P("Todas las capturas salen de las propias grabaciones del proceso, extraídas con ffmpeg, o de las vistas que generan los scripts. Para recrear una captura, ejecuta el paso correspondiente y extrae el fotograma:"),
  code(["ffmpeg -ss 25.0 -i segmento_slicer_EN.mp4 -frames:v 1 -vf scale=1600:-1 06_grow_preview.jpg"]),
  spacer(),
  table([3000, 6638], ["Captura", "Cómo se obtiene"], [
    ["00_mosaico_axial", "Script t0b.py: mosaico de cortes axiales del volumen."],
    ["01 a 15", "Fotogramas del video de 3D Slicer (segmento_slicer_EN.mp4)."],
    ["16_orcaslicer", "Fotograma del video de OrcaSlicer (segmento_orca_raw.mp4)."],
    ["17 a 22", "Fotogramas del video del simulador (segmento_simulador_EN.mp4)."],
    ["23_resumen_vistas", "Imagen generada por t4_render.py (cuatro vistas de la plantilla)."],
    ["24_segmentacion_cortes", "Imagen generada por t2_seg.py (contorno del tumor en ocho cortes)."],
  ]),
  spacer(),
  H1("Anexo C · Variante con la pelvis"),
  P("El mismo método se aplicó a un CT público de pelvis para orientar una copa acetabular: segmentación experta de los huesos coxales y el sacro, análisis de elementos finitos con carga de 200 kN, una guía con tres parches de contacto y un tubo alineado con el eje de la copa, y su preparación para impresión. Los pasos de preparación de impresión, laminado en OrcaSlicer y grabación son los mismos que en este tutorial."),
  H1("Anexo D · Referencias"),
  bullet([link("Rigidez de meningiomas por elastografía (PMC11990845)", "https://pmc.ncbi.nlm.nih.gov/articles/PMC11990845/")]),
  bullet([link("Deformación cerebral bajo una craneotomía (Neurosurgery, 1998)", "https://www.ovid.com/jnls/neurosurgery/abstract/00006123-199809000-00066~measurement-of-intraoperative-brain-surface-deformation")]),
  bullet([link("Espesor de la bóveda craneal en TC (PMC8827567)", "https://pmc.ncbi.nlm.nih.gov/articles/PMC8827567/")]),
  bullet([link("Espesor del cuero cabelludo (arXiv 2405.08489)", "https://arxiv.org/pdf/2405.08489")]),
  bullet([link("Presión intracraneal y de perfusión cerebral", "https://en.wikipedia.org/wiki/Intracranial_pressure")]),
  bullet([link("Datos de ejemplo de 3D Slicer (SlicerTestingData)", "https://github.com/Slicer/SlicerTestingData")]),
);

const numbering = {
  config: [
    { reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] },
    ...lists.map((r) => ({ reference: r, levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 360 } }, run: { bold: true, color: C.accent } } }] })),
  ],
};

const doc = new Document({
  creator: "Tutorial", title: "Tutorial: del tumor en una resonancia a una craneotomía practicable en realidad mixta",
  styles: { default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 34, bold: true, font: FONT, color: C.accent }, paragraph: { spacing: { before: 360, after: 160 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 26, bold: true, font: FONT, color: C.ink }, paragraph: { spacing: { before: 240, after: 100 }, outlineLevel: 1 } },
    ] },
  numbering,
  sections: [{
    properties: { page: { size: { width: PAGE_W, height: PAGE_H }, margin: { top: MARGIN, bottom: MARGIN, left: MARGIN, right: MARGIN } } },
    headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: C.line, space: 4 } }, children: [new TextRun({ text: "Tutorial · Tumor cerebral, plantilla de craneotomía y simulador XR", font: FONT, size: 17, color: C.muted })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "Ejercicio académico · no es un dispositivo médico · Página ", font: FONT, size: 17, color: C.muted }), new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 17, color: C.muted })] })] }) },
    children,
  }],
});

Packer.toBuffer(doc).then((buf) => { fs.writeFileSync(path.join(__dirname, "Tutorial_tumor_cerebral_XR.docx"), buf); console.log("OK", (buf.length / 1e6).toFixed(2) + " MB"); });
