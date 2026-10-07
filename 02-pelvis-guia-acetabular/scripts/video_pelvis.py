import sys, time, subprocess, json, math
sys.path.append("C:/Users/Laboratorio/Downloads/femur_vh/deps_vid")
import slicer, vtk, qt, numpy as np
import imageio_ffmpeg
from vtk.util.numpy_support import vtk_to_numpy

P = "C:/Users/Laboratorio/Downloads/pelvis_guia"
B = "C:/Users/Laboratorio/Downloads/femur_vh/s016/016/SMIR.Lower_limb.095Y.F.CT.476/"
OUT = P + "/pelvis_guia_quirurgica_redes.mp4"
FPS = 24
DT = 1.0 / FPS
H = "4.5"

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
pump(5)
_vn0 = lm.threeDWidget(0).threeDView().mrmlViewNode()
_vn0.SetBoxVisible(False)
_vn0.SetAxisLabelsVisible(False)
_vn0.SetBackgroundColor(0.05, 0.06, 0.10)
_vn0.SetBackgroundColor2(0.20, 0.26, 0.34)

# ---------- precarga silenciosa del CT de pelvis (antes de grabar) ----------
ctv = slicer.util.loadVolume(B + "SMIR.Lower_limb.095Y.F.CT.476.nrrd")
ctv.SetName("CT_pelvis_muslos")
segE = slicer.util.loadSegmentation(B + "SMIR.Lower_limb.095Y.F.CT.476-Pelvis-Thighs_Reconstruction.seg.nrrd")
segE.SetName("Segmentacion_experta")
sd = segE.GetDisplayNode()
sd.SetVisibility3D(False)
sg = segE.GetSegmentation()
for i in range(sg.GetNumberOfSegments()):
    nm = sg.GetNthSegment(i).GetName()
    sd.SetSegmentVisibility(sg.GetNthSegmentID(i), nm in ("Hip_R", "Hip_L", "Sacrum"))
sd.SetVisibility(False)
for cn in slicer.util.getNodesByClass("vtkMRMLSliceCompositeNode"):
    cn.SetBackgroundVolumeID(None)
pump(5)

slicer.util.selectModule("SampleData")
pump(5)
title = mw.windowTitle
print("TITLE", title, flush=True)

# ---------- subtítulos (QLabel superpuesto en la ventana) ----------
lbl = qt.QLabel(mw)
lbl.setAttribute(qt.Qt.WA_TransparentForMouseEvents)
lbl.setStyleSheet("background-color: rgba(0,0,0,185); color: white; padding: 8px 18px;")


def cap(a, b=""):
    lbl.setText("<div style='font-size:24px;font-weight:bold'>%s</div><div style='font-size:16px;color:#c8d6f0'>%s</div>" % (a, b))
    h = 96
    lbl.setGeometry(0, mw.height - h - 24, mw.width, h)
    lbl.show()
    lbl.raise_()


cap("3D Slicer 5.12.4", "Paso 1: probar con los datos de ejemplo oficiales (módulo SampleData)")
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

state = {"next": time.time()}


def tick(view=None):
    if view is not None:
        view.forceRender()
    pump(1)
    state["next"] += DT
    wait = state["next"] - time.time()
    if wait > 0:
        end = time.time() + wait
        while time.time() < end:
            pump(1)
    else:
        state["next"] = time.time()


def v3d():
    return lm.threeDWidget(0).threeDView()


def vn():
    return v3d().mrmlViewNode()


def cam():
    return slicer.modules.cameras.logic().GetViewActiveCameraNode(vn()).GetCamera()


def rend():
    return v3d().renderWindow().GetRenderers().GetFirstRenderer()


def hold(sec):
    for _ in range(int(sec * FPS)):
        tick(v3d())


def orbit(sec, deg, each=None):
    n = int(sec * FPS)
    for i in range(n):
        cam().Azimuth(deg / n)
        cam().OrthogonalizeViewUp()
        rend().ResetCameraClippingRange()
        if each:
            each(i / (n - 1 if n > 1 else 1))
        tick(v3d())


def reset_cam(zoom=1.0):
    slicer.util.resetThreeDViews()
    c = cam()
    fp = c.GetFocalPoint()
    dist = c.GetDistance()
    c.SetPosition(fp[0], fp[1] + dist, fp[2])
    c.SetViewUp(0, 0, 1)
    c.Zoom(zoom)
    rend().ResetCameraClippingRange()
    pump()


def focus_bounds(b, mult=1.9):
    cx, cy, cz = (b[0] + b[1]) / 2, (b[2] + b[3]) / 2, (b[4] + b[5]) / 2
    ext = max(b[1] - b[0], b[3] - b[2], b[5] - b[4])
    c = cam()
    c.SetFocalPoint(cx, cy, cz)
    c.SetPosition(cx, cy + ext * mult, cz)
    c.SetViewUp(0, 0, 1)
    rend().ResetCameraClippingRange()
    pump()


def style(node, color, opacity=1.0, edges=False):
    dn = node.GetDisplayNode()
    dn.SetColor(*color)
    dn.SetOpacity(opacity)
    dn.SetEdgeVisibility(edges)
    dn.SetScalarVisibility(False)
    dn.SetVisibility(True)
    dn.SetAmbient(0.25)
    dn.SetDiffuse(0.75)
    dn.SetSpecular(0.2)


def addpoly(name, pd):
    n = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", name)
    n.SetAndObservePolyData(pd)
    n.CreateDefaultDisplayNodes()
    return n


def hide_models():
    for n in slicer.util.getNodesByClass("vtkMRMLModelNode"):
        if n.GetDisplayNode():
            n.GetDisplayNode().SetVisibility(False)


try:
    hold(3.5)

    # ===== PASO 1: dato de ejemplo (Panoramix) =====
    cap("Paso 1: CT de ejemplo de 3D Slicer (CTA abdomen · Panoramix)", "Tórax inferior y abdomen: el CT está recortado y termina antes del acetábulo")
    pano = slicer.util.loadVolume(P + "/Panoramix-cropped.nrrd")
    slicer.util.selectModule("Data")
    pump(5)
    arr = slicer.util.arrayFromVolume(pano)
    seg = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "Hueso_umbral")
    seg.CreateDefaultDisplayNodes()
    seg.SetReferenceImageGeometryParameterFromVolumeNode(pano)
    sid = seg.GetSegmentation().AddEmptySegment("Hueso (>200 UH)")
    seg.GetSegmentation().GetSegment(sid).SetColor(0.95, 0.9, 0.7)
    hold(3.5)
    cap("Segmentación por umbral de hueso (> 200 UH)", "Se ven costillas, columna y alas ilíacas, pero faltan acetábulo, isquion y pubis")
    slicer.util.updateSegmentBinaryLabelmapFromArray((arr > 200).astype(np.uint8), seg, sid, pano)
    seg.CreateClosedSurfaceRepresentation()
    seg.GetDisplayNode().SetVisibility3D(True)
    pump(5)
    _b = [0.0] * 6
    seg.GetRASBounds(_b)
    focus_bounds(_b, 1.7)
    orbit(6.0, 200)

    # ===== PASO 2: CT completo + segmentación experta =====
    cap("Paso 2: CT público de pelvis y muslos con segmentación experta", "Segmentos: sacro, coxal derecho (Hip_R) y coxal izquierdo (Hip_L) sobre cortes axial, coronal y sagital")
    seg.GetDisplayNode().SetVisibility(False)
    pano.GetDisplayNode().SetVisibility(False) if pano.GetDisplayNode() else None
    for cn in slicer.util.getNodesByClass("vtkMRMLSliceCompositeNode"):
        cn.SetBackgroundVolumeID(ctv.GetID())
    segE.GetDisplayNode().SetVisibility(True)
    segE.GetDisplayNode().SetOpacity2DFill(0.45)
    slicer.util.selectModule("Segmentations")
    c = np.load(P + "/fea_bc_h%s.npz" % H)["head"]
    slicer.modules.markups.logic().JumpSlicesToLocation(float(c[0]), float(c[1]), float(c[2]) + 10, True)
    slicer.util.resetSliceViews()
    slicer.modules.markups.logic().JumpSlicesToLocation(float(c[0]), float(c[1]), float(c[2]) + 10, True)
    hold(7.0)

    # ===== PASO 3: modelos depurados en 3D =====
    st = json.load(open(P + "/segmentacion_estadisticas.json"))
    lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUp3DView)
    segE.GetDisplayNode().SetVisibility(False)
    pano.SetDisplayVisibility(False) if hasattr(pano, "SetDisplayVisibility") else None
    for n in slicer.util.getNodesByClass("vtkMRMLModelNode"):
        pass
    vn().SetBackgroundColor(0.05, 0.06, 0.10)
    vn().SetBackgroundColor2(0.20, 0.26, 0.34)
    vn().SetBoxVisible(False)
    vn().SetAxisLabelsVisible(False)
    mods = {}
    for nm, col in (("Hip_R", (0.88, 0.35, 0.30)), ("Hip_L", (0.35, 0.50, 0.88)), ("Sacrum", (0.30, 0.70, 0.40)), ("Femur_R", (0.90, 0.80, 0.50))):
        m = slicer.util.loadNodeFromFile(P + "/modelos/%s.stl" % nm, "ModelFile", {"coordinateSystem": "RAS"})
        m.SetName(nm)
        style(m, col)
        mods[nm] = m
    slicer.util.selectModule("Models")
    reset_cam(0.95)
    cap("Paso 3: depuración de la segmentación",
        "Isla única · huecos rellenos · suavizado · coxal derecho: %d triángulos, %.0f cm³, %d aristas abiertas"
        % (st["Hip_R"]["tri"], st["Hip_R"]["volumen_mm3"] / 1000.0, st["Hip_R"]["bordes_abiertos"]))
    orbit(8.0, 330)

    # ===== PASO 4: malla FEA del coxal derecho =====
    cap("Paso 4: análisis estructural del coxal derecho", "Malla de elementos finitos: tetraedros lineales (corte para ver el interior)")
    hide_models()
    rd = vtk.vtkXMLUnstructuredGridReader()
    rd.SetFileName(P + "/fea_pelvis_h%s.vtu" % H)
    rd.Update()
    ug = rd.GetOutput()
    X = vtk_to_numpy(ug.GetPoints().GetData())
    ctr = np.array(ug.GetCenter())
    pl = vtk.vtkPlane()
    pl.SetOrigin(*ctr)
    pl.SetNormal(1, 0, 0)
    clip = vtk.vtkClipDataSet()
    clip.SetInputData(ug)
    clip.SetClipFunction(pl)
    clip.Update()
    gf = vtk.vtkGeometryFilter()
    gf.SetInputData(clip.GetOutput())
    gf.Update()
    half = vtk.vtkPolyData()
    half.DeepCopy(gf.GetOutput())
    Bn = addpoly("malla_FEA_corte", half)
    style(Bn, (0.85, 0.85, 0.9), 1.0, True)
    Bn.GetDisplayNode().SetEdgeColor(0.15, 0.25, 0.45)
    reset_cam(0.95)
    cap("Paso 4: análisis estructural del coxal derecho",
        "Malla: %d nodos · %d tetraedros · hueso cortical (E = 17 GPa, ν = 0.3)" % (ug.GetNumberOfPoints(), ug.GetNumberOfCells()))
    orbit(5.5, 220)

    # ===== PASO 5: condiciones de contorno =====
    bc = np.load(P + "/fea_bc_h%s.npz" % H)
    fixed, load, head, Rh = bc["fixed"], bc["load"], bc["head"], float(bc["R"])
    hide_models()
    surf = vtk.vtkGeometryFilter()
    surf.SetInputData(ug)
    surf.Update()
    sp = vtk.vtkPolyData()
    sp.DeepCopy(surf.GetOutput())
    Sn = addpoly("superficie_FEA", sp)
    style(Sn, (0.9, 0.88, 0.8), 0.45)

    def spheres(idx, r, color, name):
        pts = vtk.vtkPoints()
        for i in idx:
            pts.InsertNextPoint(*X[i])
        pd = vtk.vtkPolyData()
        pd.SetPoints(pts)
        sph = vtk.vtkSphereSource()
        sph.SetRadius(r)
        sph.SetThetaResolution(10)
        sph.SetPhiResolution(10)
        g = vtk.vtkGlyph3D()
        g.SetInputData(pd)
        g.SetSourceConnection(sph.GetOutputPort())
        g.ScalingOff()
        g.Update()
        o = vtk.vtkPolyData()
        o.DeepCopy(g.GetOutput())
        n = addpoly(name, o)
        style(n, color)

    spheres(fixed, 2.4, (0.15, 0.35, 1.0), "apoyos")
    spheres(load, 2.4, (1.0, 0.2, 0.1), "zona_carga")
    res = json.load(open(P + "/fea_pelvis_h%s.json" % H))
    Fv = np.array(res["fuerza_resultante_N"])
    dv = Fv / np.linalg.norm(Fv)
    ar = vtk.vtkArrowSource()
    ar.SetTipResolution(24)
    ar.SetShaftResolution(24)
    ar.Update()
    tail = head - dv * 120.0
    axis = np.cross([1, 0, 0], dv)
    ang = math.degrees(math.acos(float(np.dot([1, 0, 0], dv))))
    tr = vtk.vtkTransform()
    tr.Translate(*tail)
    tr.RotateWXYZ(ang, *axis)
    tr.Scale(105, 105, 105)
    tf = vtk.vtkTransformPolyDataFilter()
    tf.SetInputData(ar.GetOutput())
    tf.SetTransform(tr)
    tf.Update()
    ap = vtk.vtkPolyData()
    ap.DeepCopy(tf.GetOutput())
    An = addpoly("flecha_200kN", ap)
    style(An, (1.0, 0.25, 0.1))
    reset_cam(0.95)
    cap("Paso 5: condiciones de contorno",
        "Azul: apoyo fijo (articulación sacroilíaca y sínfisis púbica) · Rojo: carga de 200 kN sobre el techo del acetábulo")
    orbit(6.0, 200)

    # ===== PASO 6: resultados =====
    hide_models()
    g2 = vtk.vtkGeometryFilter()
    g2.SetInputData(ug)
    g2.Update()
    base = vtk.vtkPolyData()
    base.DeepCopy(g2.GetOutput())
    base.GetPointData().SetActiveVectors("desplazamiento_mm")
    base.GetPointData().SetActiveScalars("von_mises_nodal_MPa")
    wv = vtk.vtkWarpVector()
    wv.SetInputData(base)
    wv.SetScaleFactor(0.0)
    wv.Update()
    out = vtk.vtkPolyData()
    out.DeepCopy(wv.GetOutput())
    Rn = addpoly("resultado_vonMises", out)
    dn = Rn.GetDisplayNode()
    dn.SetVisibility(True)
    dn.SetColor(1, 1, 1)
    dn.SetOpacity(1.0)
    dn.SetEdgeVisibility(False)
    dn.SetActiveScalarName("von_mises_nodal_MPa")
    dn.SetActiveAttributeLocation(vtk.vtkAssignAttribute.POINT_DATA)
    jet = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLColorTableNode", "AzulARojo")
    jet.SetTypeToUser()
    jet.SetNumberOfColors(256)
    stops = [(0.0, (0.0, 0.0, 0.8)), (0.25, (0.0, 0.6, 1.0)), (0.5, (0.0, 0.9, 0.2)),
             (0.75, (1.0, 0.9, 0.0)), (1.0, (1.0, 0.0, 0.0))]
    for i in range(256):
        t = i / 255.0
        for k in range(len(stops) - 1):
            if stops[k][0] <= t <= stops[k + 1][0]:
                u = (t - stops[k][0]) / (stops[k + 1][0] - stops[k][0])
                cc = [stops[k][1][j] * (1 - u) + stops[k + 1][1][j] * u for j in range(3)]
                break
        jet.SetColor(i, "c%d" % i, cc[0], cc[1], cc[2], 1.0)
    dn.SetAndObserveColorNodeID(jet.GetID())
    dn.SetScalarRangeFlag(slicer.vtkMRMLDisplayNode.UseManualScalarRange)
    dn.SetScalarRange(0, 130.0)
    dn.SetScalarVisibility(True)
    try:
        lg = slicer.modules.colors.logic().AddDefaultColorLegendDisplayNode(Rn)
        lg.SetTitleText("Von Mises (MPa)")
        lg.SetVisibility(True)
    except Exception as e:
        print("leyenda", e, flush=True)
    reset_cam(0.95)
    SC = 4.0

    def setwarp(t):
        wv.SetScaleFactor(SC * t)
        wv.Update()
        out.DeepCopy(wv.GetOutput())
        out.GetPointData().SetActiveScalars("von_mises_nodal_MPa")
        Rn.Modified()

    cap("Paso 6: resultado a 200 kN (cálculo lineal)", "Escala 0 – 130 MPa: rojo = por encima de la resistencia del hueso cortical (≈130 MPa)")
    hold(2.0)
    cap("Deformación amplificada ×4", "Desplazamiento máximo calculado: %.1f mm" % res["u_max_mm"])
    orbit(3.0, 40, each=setwarp)
    cap("Resultado: el hueso no soportaría 200 kN",
        "%.0f %% del volumen supera 130 MPa · von Mises medio %.0f MPa · percentil 99: %.0f MPa" % (
            100 * res["fraccion_volumen_sobre_130MPa"], res["vm_media"], res["vm_p99"]))
    orbit(7.0, 300)
    cap("Referencia lineal: el 1 %% más cargado llega a 130 MPa con ≈ %.0f kN" % (res["F_para_p99_130MPa_N"] / 1000),
        "Las cargas fisiológicas de la cadera son de unos 2–6 kN")
    orbit(4.0, 60)
    cap("Aviso: análisis académico con datos de un cadáver", "No sirve para uso clínico. Una guía quirúrgica real necesita validación médica y regulatoria.")
    hold(4.5)
except Exception:
    import traceback
    print("ERROR", traceback.format_exc(), flush=True)
finally:
    try:
        proc.stdin.write(b"q")
        proc.stdin.flush()
    except Exception:
        pass
    try:
        proc.wait(timeout=30)
    except Exception:
        proc.kill()
    print("REC_DONE", flush=True)
    slicer.app.quit()
