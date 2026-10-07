import sys, os, time, json, traceback
sys.path.insert(0, "C:/Users/Laboratorio/Downloads/tumor_cerebral")
import slicer, qt, vtk, numpy as np
from scipy import ndimage as ndi
from PIL import Image, ImageDraw, ImageFont, ImageGrab
import seeds as SEEDS

BASE = "C:/Users/Laboratorio/Downloads/tutorial_segmentacion"
OUT = BASE + "/capturas"
TC = "C:/Users/Laboratorio/Downloads/tumor_cerebral"
os.makedirs(OUT, exist_ok=True)
BBOX = (0, 0, 1920, 990)
RED, WHITE = (235, 40, 40), (255, 255, 255)
FONT = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 24)

mw = slicer.util.mainWindow()
mw.showMaximized()
lm = slicer.app.layoutManager()
steps = []
state = {}


def pump(n=5):
    for _ in range(n):
        slicer.app.processEvents()


def wait(sec):
    t = time.time()
    while time.time() - t < sec:
        pump(2)
        time.sleep(0.02)


def cls(w):
    try:
        return w.className()
    except Exception:
        return type(w).__name__


def text_of(w):
    try:
        t = w.text
        return t() if callable(t) else t
    except Exception:
        return ""


def find(name=None, text=None, kind=None, tip=None, nth=0):
    hits = []
    for w in mw.findChildren(qt.QWidget):
        if not w.isVisible():
            continue
        if name is not None and w.objectName != name:
            continue
        if kind is not None and kind not in cls(w):
            continue
        if text is not None and str(text_of(w)).strip() != text:
            continue
        if tip is not None:
            try:
                tp = w.toolTip
                tp = tp() if callable(tp) else tp
            except Exception:
                tp = ""
            if tip not in str(tp):
                continue
        hits.append(w)
    if len(hits) <= nth:
        raise RuntimeError("no encontrado: name=%s text=%s kind=%s tip=%s" % (name, text, kind, tip))
    return hits[nth]


def rect(w):
    g = w.mapToGlobal(qt.QPoint(0, 0))
    return (g.x(), g.y(), w.width, w.height)



def origin():
    p = mw.mapToGlobal(qt.QPoint(0, 0))
    return p.x(), p.y()


def grab_slicer():
    pump(5)
    tmp = BASE + "/_tmp_grab.png"
    mw.grab().save(tmp)
    return Image.open(tmp).convert("RGB").copy()


def grab_region_np():
    return np.asarray(grab_slicer().convert("RGB"))


def annotate(img, items, click=None):
    img = img.convert("RGBA")
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for it in items:
        x, y, w, h = it["rect"]
        pad = 6
        d.rounded_rectangle([x - pad, y - pad, x + w + pad, y + h + pad], radius=8, outline=RED + (255,), width=5)
        bx, by = x - pad - 4, y - pad - 4
        d.ellipse([bx - 15, by - 15, bx + 15, by + 15], fill=RED + (255,), outline=WHITE + (255,), width=3)
        tw = d.textlength(str(it["label"]), font=FONT)
        d.text((bx - tw / 2, by - 15), str(it["label"]), font=FONT, fill=WHITE + (255,))
    if click:
        cx, cy = click
        for r, a in ((34, 70), (22, 130), (11, 200)):
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(255, 200, 0, a), width=4)
        poly = [(0, 0), (0, 26), (7, 20), (12, 31), (17, 29), (12, 19), (21, 19)]
        d.polygon([(cx + 6 + px, cy + 4 + py) for px, py in poly], fill=(255, 255, 255, 255), outline=(0, 0, 0, 255))
    return Image.alpha_composite(img, ov).convert("RGB")


def snap(name, title, narr, items=(), click=None):
    """items: [{'rect':(x,y,w,h),'label':'1'}]; click: (x, y) en pantalla"""
    pump(10)
    wait(0.7)
    img = grab_slicer()
    ox, oy = origin()
    items = [dict(i, rect=tuple(int(v) for v in (i["rect"][0] - ox, i["rect"][1] - oy, i["rect"][2], i["rect"][3]))) for i in items]
    click = (int(click[0] - ox), int(click[1] - oy)) if click else None
    out = annotate(img, list(items), click)
    fn = "%s.png" % name
    out.save(os.path.join(OUT, fn))
    img.save(os.path.join(OUT, name + "_sin_marcas.png"))
    steps.append(dict(name=name, file=fn, title=title, narr=narr,
                      items=[dict(rect=[int(v) for v in i["rect"]], label=str(i["label"]), note=i.get("note", "")) for i in items], click=[int(v) for v in click] if click else None))
    json.dump(steps, open(BASE + "/steps.json", "w"), ensure_ascii=False, indent=1)
    print("SNAP", name, flush=True)


def it(w_or_rect, label, note=""):
    r = rect(w_or_rect) if not isinstance(w_or_rect, (tuple, list)) else tuple(w_or_rect)
    return {"rect": r, "label": str(label), "note": note}


def center(w):
    x, y, w_, h = rect(w)
    return (x + w_ // 2, y + h // 2)


def go_module(name):
    slicer.util.selectModule(name)
    pump(10)
    wait(0.8)


def view_rect(name):
    w = lm.sliceWidget(name)
    return rect(w)


def color_bbox(img, region, test):
    ox, oy = origin()
    x0, y0, x1, y1 = region[0] - ox, region[1] - oy, region[2] - ox, region[3] - oy
    a = np.asarray(img.convert("RGB"))[y0:y1, x0:x1].astype(int)
    m = test(a[..., 0], a[..., 1], a[..., 2])
    ys, xs = np.where(m)
    if len(xs) < 20:
        return None
    return (int(x0 + xs.min() + ox), int(y0 + ys.min() + oy), int(xs.max() - xs.min()), int(ys.max() - ys.min()))


def safe(label, fn):
    try:
        fn()
    except Exception:
        print("FALLO", label, traceback.format_exc(), flush=True)


# ------------------------------------------------------------------ preparacion
t0 = time.time()
while time.time() - t0 < 3:
    pump()
slicer.mrmlScene.Clear(0)
wait(2.0)
lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutConventionalView)
pump(5)
for v in (lm.threeDWidget(0).threeDView().mrmlViewNode(),):
    v.SetBoxVisible(False)
    v.SetAxisLabelsVisible(False)
ex = json.load(open(TC + "/explora.json"))
t_est = np.load(TC + "/tumor_estimacion.npy")
head = np.load(TC + "/cabeza.npy")
SP = np.array([1.4, 0.9375, 0.9375])
dhead = ndi.distance_transform_edt(head, sampling=SP)
core = SEEDS.core_from_estimate(t_est, ex["centro_kji"])
tstrokes, bstrokes = SEEDS.make_strokes(core, head, dhead, SP)

# ------------------------------------------------------------------ 01 pantalla inicial
def s01():
    go_module("Welcome")
    combo = find(kind="ctkMenuComboBox")
    panel = (0, 134, 430, 676)
    views = (432, 95, 1488, 890)
    snap("01_pantalla_inicial", "Así se ve 3D Slicer al abrirlo",
         "Esta es la pantalla de 3D Slicer. Arriba hay una lista llamada Modules para cambiar de herramienta. A la izquierda está el panel de la herramienta activa, y a la derecha, las vistas de la imagen.",
         [it(combo, 1, "lista de módulos"), it(panel, 2, "panel del módulo"), it(views, 3, "vistas")])
safe("s01", s01)


# ------------------------------------------------------------------ 02-03 SampleData
def s02():
    go_module("SampleData")
    combo = find(kind="ctkMenuComboBox")
    btn = find(name="MRBrainTumor1PushButton")
    snap("02_sampledata", "Abre el módulo SampleData y pulsa MRBrainTumor1",
         "Elige el módulo SampleData en la lista. Aquí hay casos de ejemplo. Pulsa el botón MRBrainTumor1: es una resonancia de cerebro con un tumor.",
         [it(combo, 1, "elige SampleData"), it(btn, 2, "haz clic aquí")], click=center(btn))
    btn.click()
    t = time.time()
    while time.time() - t < 90 and not slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode"):
        wait(1)
    wait(3)
    vols = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")
    if not vols:
        raise RuntimeError("no se cargo MRBrainTumor1")
    state["vol"] = vols[0]
    print("VOL", vols[0].GetName(), flush=True)
safe("s02", s02)


def s03():
    vol = state["vol"]
    go_module("SampleData")
    wait(0.5)
    snap("03_caso_cargado", "El caso se cargó: tres cortes y una vista 3D",
         "Listo. La imagen aparece en tres cortes: arriba a la izquierda el corte axial, abajo a la izquierda el coronal y abajo a la derecha el sagital. Arriba a la derecha está la vista 3D, todavía vacía.",
         [it(view_rect("Red"), 1, "axial"), it(view_rect("Green"), 2, "coronal"), it(view_rect("Yellow"), 3, "sagital"), it(rect(lm.threeDWidget(0)), 4, "vista 3D")])
safe("s03", s03)


# ------------------------------------------------------------------ 04 mover cortes
def s04():
    c = None
    vol = state["vol"]
    M = vtk.vtkMatrix4x4(); vol.GetIJKToRASMatrix(M)
    Mn = np.array([[M.GetElement(r, q) for q in range(4)] for r in range(4)])
    k0, j0, i0 = ex["centro_kji"]
    ras = (Mn[:3, :3] @ [i0, j0, k0]) + Mn[:3, 3]
    state["tumor_ras"] = ras
    slicer.modules.markups.logic().JumpSlicesToLocation(float(ras[0]), float(ras[1]), float(ras[2]), True)
    pump(10)
    slider = None
    for w in mw.findChildren(qt.QWidget):
        if w.isVisible() and w.objectName == "SliceOffsetSlider":
            r = rect(w)
            if r[0] < 1000 and r[1] < 300:
                slider = w
                break
    items = [it(view_rect("Red"), 2, "tumor visible en este corte")]
    if slider is not None:
        items.insert(0, it(slider, 1, "barra de cortes"))
    snap("04_mover_cortes", "Recorre los cortes con la barra de cada vista",
         "Para moverte por la imagen, arrastra la barra que está sobre cada corte, o usa la rueda del ratón sobre la imagen. En este corte ya se ve una masa clara y redonda: es el tumor.",
         items, click=center(slider) if slider is not None else None)
safe("s04", s04)


# ------------------------------------------------------------------ 05-07 Segment Editor
def s05():
    go_module("SegmentEditor")
    combo = find(kind="ctkMenuComboBox")
    snap("05_segment_editor", "Abre el módulo Segment Editor",
         "Cambia al módulo Segment Editor. Es la herramienta para pintar y editar segmentaciones. Aquí vas a trabajar casi todo el tutorial.",
         [it(combo, 1, "elige Segment Editor"), it((0, 134, 430, 676), 2, "panel del Segment Editor")])
safe("s05", s05)

editor = None


def s06():
    global editor
    editor = slicer.modules.segmenteditor.widgetRepresentation().self().editor
    editor.setSourceVolumeNode(state["vol"])
    wait(0.5)
    add = find(name="AddSegmentButton")
    snap("06_agregar_segmento", "Pulsa Add para crear un segmento",
         "Un segmento es una capa de pintura. Pulsa el botón Add para crear el primero. Lo usaremos para el tumor.",
         [it(add, 1, "Add")], click=center(add))
    add.click()
    wait(1)
    add.click()
    wait(1)
    seg = editor.segmentationNode()
    state["seg"] = seg
    sg = seg.GetSegmentation()
    ids = [sg.GetNthSegmentID(i) for i in range(sg.GetNumberOfSegments())]
    sg.GetSegment(ids[0]).SetName("Tumor"); sg.GetSegment(ids[0]).SetColor(1.0, 0.85, 0.1)
    sg.GetSegment(ids[1]).SetName("Healthy tissue"); sg.GetSegment(ids[1]).SetColor(0.2, 0.6, 1.0)
    state["tid"], state["bid"] = ids[0], ids[1]
    wait(1)
safe("s06", s06)


def s07():
    tbl = find(kind="SegmentsTableView")
    add = find(name="AddSegmentButton")
    snap("07_dos_segmentos", "Ahora tienes dos segmentos: Tumor y Healthy tissue",
         "Pulsa Add otra vez para tener un segundo segmento. Le pusimos nombre: Tumor, en amarillo, y Healthy tissue, que significa tejido sano, en azul. Se cambia el nombre con doble clic sobre el nombre.",
         [it(tbl, 1, "tabla de segmentos"), it(add, 2, "Add")])
safe("s07", s07)


# ------------------------------------------------------------------ 08 Paint
def options_rect():
    undo = find(name="UndoButton")
    ux, uy, uw, uh = rect(undo)
    dp = find(name="DataProbeCollapsibleWidget")
    return (0, uy + uh + 8, 430, rect(dp)[1] - (uy + uh + 8) - 6)


def s08():
    editor.setCurrentSegmentID(state["tid"])
    wait(0.5)
    paint = find(name="Paint")
    paint.click()
    wait(1.5)
    snap("08_herramienta_paint", "Elige la herramienta Paint (pincel)",
         "En la columna de herramientas elige Paint. Es el pincel. Debajo aparecen sus opciones, como el diámetro del pincel. Con el segmento Tumor seleccionado, todo lo que pintes será tumor.",
         [it(paint, 1, "Paint"), it(options_rect(), 2, "opciones del pincel")], click=center(paint))
safe("s08", s08)


# ------------------------------------------------------------------ 09-10 semillas
def paint_seeds(strokes, arr, sid):
    for s_ in strokes:
        arr[s_[:, 0], s_[:, 1], s_[:, 2]] = 1
    slicer.util.updateSegmentBinaryLabelmapFromArray(arr, state["seg"], sid, state["vol"])


def red_region():
    x, y, w, h = view_rect("Red")
    return (x + 4, y + 40, x + w - 4, y + h - 4)


def s09():
    lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUpRedSliceView)
    pump(10)
    wait(1.0)
    shape = slicer.util.arrayFromVolume(state["vol"]).shape
    mt = np.zeros(shape, np.uint8)
    state["mt"] = mt
    kc = int(round(core.nonzero()[0].mean()))
    # un corte central
    vol = state["vol"]
    M = vtk.vtkMatrix4x4(); vol.GetIJKToRASMatrix(M)
    zc = M.GetElement(2, 2) * kc + M.GetElement(2, 3)
    sn = lm.sliceWidget("Red").mrmlSliceNode()
    slicer.modules.markups.logic().JumpSlicesToLocation(float(state["tumor_ras"][0]), float(state["tumor_ras"][1]), float(zc), True)
    pump(10)
    paint_seeds(tstrokes, mt, state["tid"])
    wait(1.0)
    img = grab_slicer()
    bb = color_bbox(img, red_region(), lambda r, g, b: (r > 220) & (g > 170) & (b < 110))
    tbl = find(kind="SegmentsTableView")
    items = [it(tbl, 1, "segmento Tumor seleccionado")]
    if bb:
        items.append(it(bb, 2, "semilla del tumor"))
    snap("09_semillas_tumor", "Pinta semillas dentro del tumor",
         "Con el pincel, pinta unos trazos dentro del tumor, sin llegar al borde. No hace falta cubrirlo entero: bastan unas cuantas manchas bien al centro, en tres o cuatro cortes distintos.",
         items)
safe("s09", s09)


def s10():
    editor.setCurrentSegmentID(state["bid"])
    wait(0.5)
    mb = np.zeros_like(state["mt"])
    state["mb"] = mb
    paint_seeds(bstrokes, mb, state["bid"])
    wait(1.0)
    img = grab_slicer()
    bb = color_bbox(img, red_region(), lambda r, g, b: (b > 200) & (g > 120) & (g < 200) & (r < 110))
    tbl = find(kind="SegmentsTableView")
    items = [it(tbl, 1, "ahora Healthy tissue")]
    if bb:
        items.append(it(bb, 2, "semillas del tejido sano"))
    snap("10_semillas_sano", "Pinta semillas en el tejido sano de alrededor",
         "Ahora elige el segmento Healthy tissue y pinta un anillo de azul alrededor del tumor, sin tocarlo. También pinta sobre la línea fina del centro, la hoz, para que el tumor no se escape por ahí.",
         items)
safe("s10", s10)


# ------------------------------------------------------------------ 11-13 Grow from seeds
def s11():
    lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
    pump(10)
    wait(1.0)
    slicer.modules.markups.logic().JumpSlicesToLocation(*[float(x) for x in state["tumor_ras"]], True)
    pump(5)
    editor.setCurrentSegmentID(state["tid"])
    g = find(name="Grow from seeds")
    snap("11_grow_from_seeds", "Elige Grow from seeds",
         "Elige la herramienta Grow from seeds, que significa hacer crecer las semillas. Con ella el programa decide solo, en 3D, hasta dónde llega el tumor y dónde empieza el tejido sano.",
         [it(g, 1, "Grow from seeds")], click=center(g))
    g.click()
    wait(1.5)
safe("s11", s11)


def s12():
    init = find(kind="Button", text="Initialize")
    snap("12_initialize", "Pulsa Initialize para ver la vista previa",
         "Pulsa Initialize. El programa calcula una vista previa: en los tres cortes verás el tumor en amarillo y el tejido sano en azul, creciendo hasta tocarse.",
         [it(init, 1, "Initialize")], click=center(init))
    init.click()
    wait(5)
    ap = find(kind="Button", text="Apply")
    snap("13_vista_previa", "Revisa la vista previa y pulsa Apply",
         "Revisa que el borde amarillo siga el borde del tumor en los tres cortes. Si se ve bien, pulsa Apply para aceptar el resultado.",
         [it(ap, 1, "Apply")], click=center(ap))
    ap.click()
    wait(4)
    snap("14_grow_aplicado", "Resultado: el tumor quedó marcado en todos los cortes",
         "Listo. El tumor quedó marcado en todos los cortes con solo unos trazos. Un umbral simple no lo habría logrado, porque la hoz y los vasos también se ven brillantes.",
         [it(view_rect("Red"), 1, "axial"), it(view_rect("Green"), 2, "coronal"), it(view_rect("Yellow"), 3, "sagital")])
safe("s12", s12)


# ------------------------------------------------------------------ 15-16 limpiar
def s13():
    editor.setCurrentSegmentID(state["tid"])
    wait(0.5)
    sm = find(name="Smoothing")
    sm.click()
    wait(1.5)
    eff = editor.activeEffect()
    eff.setParameter("SmoothingMethod", "MEDIAN")
    eff.setParameter("KernelSizeMm", 3.0)
    wait(1.0)
    ap = find(kind="Button", text="Apply")
    snap("15_suavizado", "Suaviza el borde con Smoothing (Median, 3 mm)",
         "Elige Smoothing. Deja el método Median con tamaño de 3 milímetros y pulsa Apply. Así se redondean las puntas y desaparecen los puntos sueltos.",
         [it(sm, 1, "Smoothing"), it(ap, 2, "Apply")], click=center(ap))
    ap.click()
    wait(3)
safe("s13", s13)


def s14():
    isl = find(name="Islands")
    isl.click()
    wait(1.5)
    eff = editor.activeEffect()
    eff.setParameter("Operation", "KEEP_LARGEST_ISLAND")
    wait(1.0)
    ap = find(kind="Button", text="Apply")
    snap("16_islas", "Quita fragmentos sueltos con Islands (Keep largest island)",
         "Elige Islands y la opción Keep largest island, que significa quedarse con la isla más grande. Pulsa Apply. Así queda solo el tumor y se borran los restos aislados.",
         [it(isl, 1, "Islands"), it(ap, 2, "Apply")], click=center(ap))
    ap.click()
    wait(3)
    editor.setActiveEffectByName("")
    state["seg"].GetDisplayNode().SetSegmentVisibility(state["bid"], False)
    wait(1)
safe("s14", s14)


# ------------------------------------------------------------------ 17 3D
def s15():
    show3d = find(name="Show3DButton")
    snap("17_ver_en_3d", "Pulsa Show 3D para ver el tumor en tres dimensiones",
         "Pulsa el botón Show 3D. El tumor aparece en la vista 3D de arriba a la derecha. Puedes girarlo arrastrando con el ratón.",
         [it(show3d, 1, "Show 3D"), it(rect(lm.threeDWidget(0)), 2, "vista 3D")], click=center(show3d))
    state["seg"].CreateClosedSurfaceRepresentation()
    state["seg"].GetDisplayNode().SetVisibility3D(True)
    wait(3)
    v3 = lm.threeDWidget(0).threeDView()
    v3.rotateToViewAxis(3)
    v3.resetFocalPoint()
    wait(2)
    snap("18_modelo_3d", "El modelo 3D del tumor",
         "Este es el modelo 3D de lo que segmentaste. Gíralo con el ratón para mirarlo desde todos los lados.",
         [it(rect(lm.threeDWidget(0)), 1, "modelo 3D del tumor")])
safe("s15", s15)


# ------------------------------------------------------------------ 19-20 estadisticas
def s16():
    go_module("SegmentStatistics")
    combos = [w for w in mw.findChildren(qt.QWidget) if w.isVisible() and "NodeComboBox" in cls(w)]
    for c_ in combos:
        try:
            tp = c_.toolTip
            tp = tp() if callable(tp) else tp
        except Exception:
            tp = ""
        if "scalar volume" in str(tp).lower():
            c_.setCurrentNode(state["vol"])
        elif "segmentation to compute" in str(tp).lower():
            c_.setCurrentNode(state["seg"])
    wait(1.0)
    combos = [w for w in mw.findChildren(qt.QWidget) if w.isVisible() and "NodeComboBox" in cls(w)]
    apply_btn = find(kind="Button", text="Apply")
    snap("19_segment_statistics", "Abre Segment Statistics y pulsa Apply",
         "Cambia al módulo Segment Statistics. En Segmentation debe estar tu segmentación y en Scalar volume la resonancia. Pulsa Apply para que el programa calcule las medidas.",
         [it((rect(combos[1])[0], rect(combos[1])[1], rect(combos[1])[2], rect(combos[2])[1] + rect(combos[2])[3] - rect(combos[1])[1]) if len(combos) > 2 else rect(apply_btn), 1, "tu segmentación y la imagen"), it(apply_btn, 2, "Apply")], click=center(apply_btn))
    apply_btn.click()
    wait(4)
    snap("20_resultados", "Resultados: volumen, tamaño e intensidad",
         "La tabla muestra el volumen del tumor, unos 16,9 centímetros cúbicos, su diámetro máximo y la intensidad media. Estos números salen de contar los vóxeles que pintaste.",
         [it((432, 95, 1488, 890), 1, "tabla de resultados")])
safe("s16", s16)

print("FIN", len(steps), flush=True)
slicer.app.quit()
