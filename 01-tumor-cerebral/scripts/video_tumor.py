import sys, time, subprocess, json, math, traceback
sys.path.append("C:/Users/Laboratorio/Downloads/femur_vh/deps_vid")
sys.path.insert(0, "C:/Users/Laboratorio/Downloads/tumor_cerebral")
import slicer, vtk, qt, numpy as np
import imageio_ffmpeg
from scipy import ndimage as ndi
import seeds

P = "C:/Users/Laboratorio/Downloads/tumor_cerebral"
OUT = P + "/segmento_slicer_EN.mp4"
FPS = 24
DT = 1.0 / FPS
stats_js = json.load(open(P + "/estadisticas_segmentos.json"))
plan = json.load(open(P + "/plan_craneotomia.json"))
imp = json.load(open(P + "/impresion_plan.json"))
geo = np.load(P + "/plan_geom.npz")
c_t, entry, d = geo["c_t"], geo["entry"], geo["d"]
T_ = stats_js["Tumor"]
R_ = stats_js["Referencia_sustancia_blanca_derecha"]


def gv(dct, key):
    for k, v in dct.items():
        if k.endswith("." + key):
            return v
    return None


mw = slicer.util.mainWindow()
mw.showMaximized()
mw.raise_()
mw.activateWindow()


def pump(n=3):
    for _ in range(n):
        slicer.app.processEvents()


t0 = time.time()
while time.time() - t0 < 3:
    pump()
lm = slicer.app.layoutManager()
lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
slicer.util.selectModule("SampleData")
pump(5)

# ---------- precalculo de semillas (antes de grabar) ----------
ex = json.load(open(P + "/explora.json"))
t_est = np.load(P + "/tumor_estimacion.npy")
head = np.load(P + "/cabeza.npy")
SP = np.array([1.4, 0.9375, 0.9375])
dhead = ndi.distance_transform_edt(head, sampling=SP)
core = seeds.core_from_estimate(t_est, ex["centro_kji"])
tstrokes, bstrokes = seeds.make_strokes(core, head, dhead, SP)

title = mw.windowTitle
print("TITLE", title, flush=True)

lbl = qt.QLabel(mw)
lbl.setAttribute(qt.Qt.WA_TransparentForMouseEvents)
lbl.setStyleSheet("background-color: rgba(0,0,0,190); color: white; padding: 8px 18px;")
card = qt.QLabel(mw)
card.setAttribute(qt.Qt.WA_TransparentForMouseEvents)
card.setWordWrap(True)
card.setAlignment(qt.Qt.AlignLeft | qt.Qt.AlignVCenter)
card.setStyleSheet("background-color: #0d1117; color: #e8edf5; padding: 40px 90px;")
card.hide()


def cap(a, b2=""):
    lbl.setText("<div style='font-size:26px;font-weight:bold'>%s</div><div style='font-size:17px;color:#c8d6f0'>%s</div>" % (a, b2))
    lbl.setGeometry(0, mw.height - 120, mw.width, 96)
    lbl.show()
    lbl.raise_()


cap("3D Slicer · brain tumor segmentation", "Sample data module: MRBrainTumor1 (contrast-enhanced T1-weighted MRI)")
pump(5)

ff = imageio_ffmpeg.get_ffmpeg_exe()
cmd = [ff, "-y", "-hide_banner", "-loglevel", "error", "-f", "gdigrab", "-framerate", str(FPS), "-draw_mouse", "0",
       "-i", "title=" + title, "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-preset", "veryfast",
       "-crf", "20", "-pix_fmt", "yuv420p", OUT]
proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
time.sleep(1.5)
if proc.poll() is not None:
    print("FFMPEG_FAIL", proc.stderr.read().decode(errors="ignore")[:500], flush=True)
    slicer.app.quit()
    sys.exit(1)
print("FFMPEG_OK", flush=True)
tstart = time.time()
state = {"next": time.time()}


def scene(name):
    print("SCENE %-14s %.2f" % (name, time.time() - tstart), flush=True)


def v3d():
    return lm.threeDWidget(0).threeDView()


def tick():
    try:
        v = v3d()
        v.renderWindow().GetRenderers().GetFirstRenderer().ResetCameraClippingRange()
        v.forceRender()
    except Exception:
        pass
    pump(1)
    state["next"] += DT
    wait = state["next"] - time.time()
    if wait > 0:
        end = time.time() + wait
        while time.time() < end:
            pump(1)
    else:
        state["next"] = time.time()


def hold(sec):
    for _ in range(int(sec * FPS)):
        tick()


def cam():
    return slicer.modules.cameras.logic().GetViewActiveCameraNode(v3d().mrmlViewNode()).GetCamera()


def set_view(focal, direction, dist, up=(0, 0, 1)):
    dd = np.array(direction, float); dd /= np.linalg.norm(dd)
    c = cam(); c.SetFocalPoint(*focal); c.SetPosition(*(np.array(focal) + dd * dist)); c.SetViewUp(*up)


def orbit(sec, deg, each=None):
    n = int(sec * FPS)
    a = np.radians(deg / n); ca, sa = np.cos(a), np.sin(a)
    for i in range(n):
        c = cam(); f = np.array(c.GetFocalPoint()); p = np.array(c.GetPosition()) - f
        p = np.array([ca * p[0] - sa * p[1], sa * p[0] + ca * p[1], p[2]])
        c.SetPosition(*(f + p)); c.SetViewUp(0, 0, 1)
        if each:
            each(i / max(n - 1, 1))
        tick()


def style3d():
    vn = v3d().mrmlViewNode()
    vn.SetBoxVisible(False); vn.SetAxisLabelsVisible(False)
    vn.SetBackgroundColor(0.05, 0.06, 0.10); vn.SetBackgroundColor2(0.20, 0.26, 0.34)


def load(fn, col, op=1.0, vis=False):
    m = slicer.util.loadNodeFromFile(P + "/" + fn, "ModelFile", {"coordinateSystem": "RAS"})
    dn = m.GetDisplayNode(); dn.SetColor(*col); dn.SetOpacity(op)
    dn.SetAmbient(0.25); dn.SetDiffuse(0.8); dn.SetSpecular(0.25); dn.SetVisibility(vis)
    dn.SetVisibility2D(False)
    return m


try:
    style3d()
    hold(3.0)
    # ===== 1. cargar el dato de ejemplo =====
    scene("load")
    vol = slicer.util.loadVolume(P + "/MRBrainTumor1.nrrd")
    vol.SetName("MRBrainTumor1")
    slicer.util.setSliceViewerLayers(background=vol, fit=True)
    M = vtk.vtkMatrix4x4(); vol.GetIJKToRASMatrix(M)
    Mn = np.array([[M.GetElement(r, c) for c in range(4)] for r in range(4)])

    def ras_of(k, j, i):
        return (Mn[:3, :3] @ [i, j, k]) + Mn[:3, 3]

    slicer.modules.markups.logic().JumpSlicesToLocation(*[float(x) for x in c_t], True)
    cap("1 · Load the sample MRI", "A well-defined, contrast-enhancing frontal mass next to the midline")
    hold(5.0)

    # ===== 2. Segment Editor =====
    scene("editor")
    slicer.util.selectModule("SegmentEditor")
    pump(5)
    editor = slicer.modules.segmenteditor.widgetRepresentation().self().editor
    seg = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "Segmentation")
    seg.CreateDefaultDisplayNodes()
    seg.SetReferenceImageGeometryParameterFromVolumeNode(vol)
    sg = seg.GetSegmentation()
    tid = sg.AddEmptySegment("Tumor", "Tumor"); sg.GetSegment(tid).SetColor(1.0, 0.85, 0.1)
    bid = sg.AddEmptySegment("Healthy", "Healthy tissue"); sg.GetSegment(bid).SetColor(0.2, 0.6, 1.0)
    seg.GetDisplayNode().SetOpacity2DFill(0.55)
    editor.setSegmentationNode(seg)
    try:
        editor.setSourceVolumeNode(vol)
    except AttributeError:
        editor.setMasterVolumeNode(vol)
    editor.setCurrentSegmentID(tid)
    editor.setActiveEffectByName("Paint")
    lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUpRedSliceView)
    pump(5)
    red = lm.sliceWidget("Red")
    rn = red.mrmlSliceNode()
    cap("2 · Segment Editor: two segments", "Tumor (yellow) and Healthy tissue (blue) · Paint tool")
    hold(3.0)

    # ===== 3. semillas =====
    scene("seeds")
    mt = np.zeros(slicer.util.arrayFromVolume(vol).shape, np.uint8)
    mb = np.zeros_like(mt)

    def paint(strokes, arr, sid, caption, sub, sec_per_stroke):
        cap(caption, sub)
        for s_ in strokes:
            k = int(s_[0, 0])
            ras = ras_of(k, s_[:, 1].mean(), s_[:, 2].mean())
            slicer.modules.markups.logic().JumpSlicesToLocation(float(ras[0]), float(ras[1]), float(ras[2]), True)
            rn.SetFieldOfView(140, 140 * rn.GetFieldOfView()[1] / max(rn.GetFieldOfView()[0], 1), rn.GetFieldOfView()[2])
            nfr = max(int(sec_per_stroke * FPS / 2), 1)
            chunks = np.array_split(np.arange(len(s_)), nfr)
            for ch in chunks:
                arr[s_[ch, 0], s_[ch, 1], s_[ch, 2]] = 1
                slicer.util.updateSegmentBinaryLabelmapFromArray(arr, seg, sid, vol)
                tick(); tick()

    paint(tstrokes, mt, tid, "3 · Paint seeds inside the tumor", "Seed strokes on a few axial slices (scripted, as in the PerkLab tutorial)", 1.4)
    editor.setCurrentSegmentID(bid)
    paint(bstrokes, mb, bid, "Paint seeds in the healthy tissue around it", "Including the falx, so the tumor does not leak along it", 1.2)

    # ===== 4. Grow from seeds =====
    scene("grow")
    lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
    pump(5)
    slicer.modules.markups.logic().JumpSlicesToLocation(*[float(x) for x in c_t], True)
    editor.setActiveEffectByName("Grow from seeds")
    eff = editor.activeEffect()
    cap("4 · Grow from seeds", "The seeds grow in 3D until tumor and healthy tissue meet (preview)")
    tick()
    eff.self().onPreview()
    hold(4.0)
    eff.self().onApply()
    cap("Grow from seeds: applied", "The whole tumor is now labeled in all slices")
    hold(2.5)

    # ===== 5. suavizado + islas =====
    scene("smooth")
    editor.setCurrentSegmentID(tid)
    editor.setActiveEffectByName("Smoothing")
    eff = editor.activeEffect(); eff.setParameter("SmoothingMethod", "MEDIAN"); eff.setParameter("KernelSizeMm", 3.0)
    cap("5 · Clean up: median smoothing (3 mm) + keep largest island", "Removes small spurs and isolated voxels")
    tick()
    eff.self().onApply()
    editor.setActiveEffectByName("Islands")
    eff = editor.activeEffect(); eff.setParameter("Operation", "KEEP_LARGEST_ISLAND")
    eff.self().onApply()
    editor.setActiveEffectByName(None)
    seg.GetDisplayNode().SetSegmentVisibility(bid, False)
    hold(3.0)

    # ===== 6. 3D =====
    scene("3d")
    seg.CreateClosedSurfaceRepresentation()
    lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUp3DView)
    pump(5)
    style3d()
    skin = load("piel.stl", (0.93, 0.78, 0.68), 0.25, True)
    set_view(c_t, (-0.4, 1.0, 0.45), 420)
    cap("6 · 3D model of the tumor", "Inside the head surface (scalp shown semi-transparent)")
    orbit(6.0, 140)

    # ===== 7. estadisticas =====
    scene("stats")
    sg.RemoveSegment(bid)
    rid = sg.AddEmptySegment("WMref", "White matter reference"); sg.GetSegment(rid).SetColor(0.3, 0.9, 0.4)
    ijk_r = np.array([0, 0, 0])
    cr = np.array(gv(R_, "centroid_ras"))
    Mi = np.linalg.inv(Mn)
    ijkr = (Mi[:3, :3] @ cr) + Mi[:3, 3]
    a_ = slicer.util.arrayFromVolume(vol)
    kk, jj, ii = np.meshgrid(np.arange(a_.shape[0]), np.arange(a_.shape[1]), np.arange(a_.shape[2]), indexing="ij")
    refm = (((kk - ijkr[2]) * SP[0]) ** 2 + ((jj - ijkr[1]) * SP[1]) ** 2 + ((ii - ijkr[0]) * SP[2]) ** 2) < 36
    slicer.util.updateSegmentBinaryLabelmapFromArray(refm.astype(np.uint8), seg, rid, vol)
    slicer.util.selectModule("SegmentStatistics")
    pump(5)
    import SegmentStatistics
    lgc = SegmentStatistics.SegmentStatisticsLogic()
    pn = lgc.getParameterNode()
    pn.SetParameter("Segmentation", seg.GetID()); pn.SetParameter("ScalarVolume", vol.GetID())
    for f in ("feret_diameter_mm", "roundness", "surface_area_mm2"):
        pn.SetParameter("LabelmapSegmentStatisticsPlugin.%s.enabled" % f, "True")
    lgc.computeStatistics()
    st = lgc.getStatistics()
    tumor_arr = slicer.util.arrayFromSegmentBinaryLabelmap(seg, tid, vol).astype(bool)
    tab = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTableNode", "Tumor measurements")
    rows = [("Volume", "%.2f cm³" % (tumor_arr.sum() * SP.prod() / 1000.0), "-"),
            ("Max. diameter (Feret)", "%.1f mm" % gv(T_, "feret_diameter_mm"), "-"),
            ("Roundness (1 = sphere)", "%.2f" % gv(T_, "roundness"), "-"),
            ("Surface area", "%.0f mm²" % gv(T_, "surface_area_mm2"), "-"),
            ("Mean intensity", "%.0f" % gv(T_, "mean"), "%.0f" % gv(R_, "mean")),
            ("Std. deviation", "%.0f" % gv(T_, "stdev"), "%.0f" % gv(R_, "stdev")),
            ("Coefficient of variation", "%.0f %%" % (100 * gv(T_, "stdev") / gv(T_, "mean")), "%.0f %%" % (100 * gv(R_, "stdev") / gv(R_, "mean")))]
    cols = []
    for nm in ("Measurement", "Tumor", "White matter (reference)"):
        c_ = vtk.vtkStringArray(); c_.SetName(nm); cols.append(c_)
    for r in rows:
        for c_, val in zip(cols, r):
            c_.InsertNextValue(val)
    for c_ in cols:
        tab.AddColumn(c_)
    lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpTableView)
    pump(5)
    slicer.app.applicationLogic().GetSelectionNode().SetActiveTableID(tab.GetID())
    slicer.app.applicationLogic().PropagateTableSelection()
    slicer.modules.markups.logic().JumpSlicesToLocation(*[float(x) for x in c_t], True)
    cap("7 · Segment Statistics", "Volume %.1f cm³ · max. diameter %.1f mm · roundness %.2f" % (tumor_arr.sum() * SP.prod() / 1000.0, gv(T_, "feret_diameter_mm"), gv(T_, "roundness")))
    hold(7.0)

    # ===== 8. analisis de tejido (histograma) =====
    scene("tissue")
    bins = np.arange(0, 330, 10)
    ht, _ = np.histogram(a_[tumor_arr], bins=bins); hr, _ = np.histogram(a_[refm], bins=bins)
    ht = 100.0 * ht / ht.sum(); hr = 100.0 * hr / hr.sum()
    tb = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTableNode", "Histogram")
    for nm, arr in (("Intensity", (bins[:-1] + 5).astype(float)), ("Tumor (%)", ht), ("White matter (%)", hr)):
        c_ = vtk.vtkDoubleArray(); c_.SetName(nm)
        for val in arr:
            c_.InsertNextValue(float(val))
        tb.AddColumn(c_)
    chart = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLPlotChartNode", "Tissue analysis")
    for nm, col in (("Tumor (%)", (1.0, 0.75, 0.0)), ("White matter (%)", (0.2, 0.8, 0.3))):
        ser = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLPlotSeriesNode", nm)
        ser.SetAndObserveTableNodeID(tb.GetID()); ser.SetXColumnName("Intensity"); ser.SetYColumnName(nm)
        ser.SetPlotType(slicer.vtkMRMLPlotSeriesNode.PlotTypeScatter); ser.SetMarkerStyle(slicer.vtkMRMLPlotSeriesNode.MarkerStyleNone)
        ser.SetLineWidth(4); ser.SetColor(*col)
        chart.AddAndObservePlotSeriesNodeID(ser.GetID())
    chart.SetTitle("Intensity histogram: tumor vs. white matter"); chart.SetXAxisTitle("MRI intensity"); chart.SetYAxisTitle("% of voxels")
    slicer.modules.plots.logic().ShowChartInLayout(chart)
    pump(5)
    slicer.modules.markups.logic().JumpSlicesToLocation(*[float(x) for x in cr], True)
    ratio = gv(T_, "mean") / gv(R_, "mean")
    cap("8 · Tissue analysis", "The tumor enhances %.1f× more than white matter and is more heterogeneous (CV %.0f %% vs %.0f %%)"
        % (ratio, 100 * gv(T_, "stdev") / gv(T_, "mean"), 100 * gv(R_, "stdev") / gv(R_, "mean")))
    hold(8.0)

    # ===== 9. planificacion =====
    scene("plan")
    lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUp3DView)
    slicer.util.selectModule("Models")
    pump(5)
    style3d()
    seg.GetDisplayNode().SetVisibility(False)
    tum = load("tumor_modelo.stl", (1.0, 0.82, 0.1), 1.0, True)
    tra = load("trayectoria.stl", (1.0, 0.35, 0.1), 1.0, True)
    out = load("contorno_craneotomia.stl", (1.0, 0.15, 0.15), 1.0, False)
    tpl = load("plantilla_craneotomia.stl", (0.10, 0.75, 0.70), 1.0, False)
    skin.GetDisplayNode().SetOpacity(0.35)
    mid = (c_t + entry) / 2
    set_view(mid, (-0.6, 0.7, 0.5), 330)
    cap("9 · Plan the approach", "Shortest path from the tumor to the scalp, entering ≥ 15 mm from the midline (superior sagittal sinus)")
    orbit(5.0, 60)
    out.GetDisplayNode().SetVisibility(True)
    cap("Craniotomy outline", "Convex tumor projection + 10 mm margin (≈ %d mm) · depth to tumor ≈ %.0f mm" % (plan["diametro_max_ventana_mm"], plan["profundidad_piel_superficie_tumor_mm"]))
    orbit(5.0, 60)

    # ===== 10. plantilla =====
    scene("template")
    dn = tpl.GetDisplayNode(); dn.SetOpacity(0.0); dn.SetVisibility(True)
    cap("10 · Craniotomy template", "Rests on the scalp; its window marks the planned craniotomy")
    for i in range(1, 25):
        dn.SetOpacity(i / 24.0); tick()
    orbit(6.0, 160)
    vn = v3d().mrmlViewNode()
    vn.SetRenderMode(slicer.vtkMRMLViewNode.Orthographic)
    set_view(entry, tuple(d), 260, up=(0, 1, 0))
    cam().SetParallelScale(75)
    cap("View along the planned trajectory", "The tumor lies inside the window with a 10 mm margin")
    hold(4.0)
    vn.SetRenderMode(slicer.vtkMRMLViewNode.Perspective)

    # ===== 11. preparacion de impresion =====
    scene("print")
    for n in (skin, tum, tra, out, tpl):
        n.GetDisplayNode().SetVisibility(False)
    ctab = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLColorTableNode", "overhang")
    ctab.SetTypeToUser(); ctab.SetNumberOfColors(256)
    for i in range(256):
        ctab.SetColor(i, "c%d" % i, *((0.86, 0.86, 0.80) if i < 128 else (1.0, 0.15, 0.10)), 1.0)
    for fn in ("imprimir_plantilla_voladizos.vtp", "imprimir_maniqui_voladizos.vtp", "imprimir_tumor_voladizos.vtp"):
        rdr = vtk.vtkXMLPolyDataReader(); rdr.SetFileName(P + "/" + fn); rdr.Update()
        pdx = vtk.vtkPolyData(); pdx.DeepCopy(rdr.GetOutput())
        m = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", fn[:-4]); m.SetAndObservePolyData(pdx); m.CreateDefaultDisplayNodes()
        d_ = m.GetDisplayNode(); d_.SetActiveScalarName("voladizo"); d_.SetActiveAttributeLocation(vtk.vtkAssignAttribute.CELL_DATA)
        d_.SetAndObserveColorNodeID(ctab.GetID()); d_.SetScalarRangeFlag(slicer.vtkMRMLDisplayNode.UseManualScalarRange)
        d_.SetScalarRange(0, 1); d_.SetScalarVisibility(True)
    cube = vtk.vtkCubeSource(); cube.SetBounds(-110, 110, -110, 110, -3, 0); cube.Update()
    bp = vtk.vtkPolyData(); bp.DeepCopy(cube.GetOutput())
    bed = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", "bed"); bed.SetAndObservePolyData(bp); bed.CreateDefaultDisplayNodes()
    bed.GetDisplayNode().SetColor(0.38, 0.42, 0.48)
    set_view((0, 10, 35), (0, -1, 0.6), 380)
    e_ = imp["estimacion_K1C"]
    cap("11 · Prepare for 3D printing", "Template (on its edge) · fit-test scalp phantom (flat base) · 1:1 tumor model · red = overhang > 45°")
    orbit(7.0, 140)
    hold(0.5)
except Exception:
    print("ERROR", traceback.format_exc(), flush=True)
finally:
    print("DURACION_s", round(time.time() - tstart, 1), flush=True)
    try:
        proc.stdin.write(b"q"); proc.stdin.flush()
    except Exception:
        pass
    try:
        proc.wait(timeout=30)
    except Exception:
        proc.kill()
    print("REC_DONE", flush=True)
    slicer.app.quit()
