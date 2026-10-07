import sys, time, subprocess
sys.path.append("C:/Users/Laboratorio/Downloads/femur_vh/deps_vid")
import slicer, vtk, qt, numpy as np
import imageio_ffmpeg
from vtk.util.numpy_support import vtk_to_numpy

d = "C:/Users/Laboratorio/Downloads/femur_vh"
OUT = d + "/femur_slicer_FEA_pantalla.mp4"
FPS = 24
DT = 1.0 / FPS

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

slicer.app.layoutManager().setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUp3DView)
tw = slicer.app.layoutManager().threeDWidget(0)
view = tw.threeDView()
vn = view.mrmlViewNode()
vn.SetBackgroundColor(0.05, 0.06, 0.10)
vn.SetBackgroundColor2(0.20, 0.22, 0.30)
vn.SetBoxVisible(False)
vn.SetAxisLabelsVisible(False)
slicer.util.selectModule("Data")
pump(5)

title = mw.windowTitle
print("TITLE", title, flush=True)
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

renderer = view.renderWindow().GetRenderers().GetFirstRenderer()
actor = vtk.vtkTextActor()
actor.GetTextProperty().SetFontSize(22)
actor.GetTextProperty().SetColor(1, 1, 1)
actor.GetTextProperty().SetBackgroundColor(0, 0, 0)
actor.GetTextProperty().SetBackgroundOpacity(0.55)
actor.GetTextProperty().SetFontFamilyToArial()
actor.SetPosition(14, 14)
renderer.AddViewProp(actor)
state = {"next": time.time()}


def tick(text=None):
    if text is not None:
        actor.SetInput(text)
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


def cam():
    return slicer.modules.cameras.logic().GetViewActiveCameraNode(vn).GetCamera()


def hold(seconds, text):
    for _ in range(int(seconds * FPS)):
        tick(text)


def orbit(seconds, deg, text, each=None):
    n = int(seconds * FPS)
    for i in range(n):
        cam().Azimuth(deg / n)
        cam().OrthogonalizeViewUp()
        renderer.ResetCameraClippingRange()
        if each:
            each(i / (n - 1 if n > 1 else 1))
        tick(text)


def reset_cam(zoom=1.0):
    slicer.util.resetThreeDViews()
    c = cam()
    fp = c.GetFocalPoint()
    dist = c.GetDistance()
    c.SetPosition(fp[0], fp[1] + dist, fp[2])
    c.SetViewUp(0, 0, 1)
    c.Zoom(zoom * 0.95)
    renderer.ResetCameraClippingRange()
    pump()


def hide_all():
    for n in slicer.util.getNodesByClass("vtkMRMLModelNode"):
        if n.GetDisplayNode():
            n.GetDisplayNode().SetVisibility(False)


def style(node, color, opacity=1.0, edges=False):
    dn = node.GetDisplayNode()
    dn.SetColor(*color)
    dn.SetOpacity(opacity)
    dn.SetEdgeVisibility(edges)
    dn.SetScalarVisibility(False)
    dn.SetVisibility(True)
    dn.SetAmbient(0.25)
    dn.SetDiffuse(0.75)
    dn.SetSpecular(0.25)


def addpoly(name, pd):
    n = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", name)
    n.SetAndObservePolyData(pd)
    n.CreateDefaultDisplayNodes()
    return n


try:
    # ---------- A: carga ----------
    hold(2.0, "3D Slicer 5.12.4 - escena vacia")
    Lm = slicer.util.loadModel(d + "/s016/016/Models/Femur_L.ply")
    style(Lm, (0.93, 0.88, 0.75))
    reset_cam(1.0)
    hold(2.0, "Modelo cargado: Femur_L (femur izquierdo, ~600 000 triangulos)")
    Rm = slicer.util.loadModel(d + "/s016/016/Models/Femur_R.ply")
    style(Rm, (0.72, 0.86, 0.93))
    reset_cam(1.0)
    hold(2.0, "Modelo cargado: Femur_R (femur derecho) - escala real ~392 mm")
    slicer.util.selectModule("Models")
    pump(5)
    orbit(6.0, 360, "Femures izquierdo y derecho - modulo Models")

    # ---------- B: malla FEA ----------
    rd = vtk.vtkXMLUnstructuredGridReader()
    rd.SetFileName(d + "/fea_femur_L_h3.5.vtu")
    rd.Update()
    ug = rd.GetOutput()
    X = vtk_to_numpy(ug.GetPoints().GetData())
    hide_all()
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
    reset_cam(1.0)
    orbit(5.0, 200, "Analisis FEA: malla de %d nodos / %d tetraedros (corte para ver el interior)"
          % (ug.GetNumberOfPoints(), ug.GetNumberOfCells()))

    # ---------- C: condiciones de contorno ----------
    hide_all()
    surf = vtk.vtkGeometryFilter()
    surf.SetInputData(ug)
    surf.Update()
    sp = vtk.vtkPolyData()
    sp.DeepCopy(surf.GetOutput())
    Sn = addpoly("superficie_FEA", sp)
    style(Sn, (0.9, 0.88, 0.8), 0.45)
    zmin = X[:, 2].min()
    fixed = np.where(X[:, 2] < zmin + 4.0)[0]
    top = int(np.argmax(X[:, 2]))
    pa = np.where(np.linalg.norm(X - X[top], axis=1) < 8.0)[0]

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

    spheres(fixed, 1.6, (0.15, 0.35, 1.0), "apoyo_fijo")
    spheres(pa, 1.6, (1.0, 0.2, 0.1), "zona_carga")
    ar = vtk.vtkArrowSource()
    ar.SetTipResolution(24)
    ar.SetShaftResolution(24)
    ar.Update()
    tr = vtk.vtkTransform()
    tr.Translate(X[top][0], X[top][1], X[top][2] + 70)
    tr.RotateY(90)
    tr.Scale(68, 68, 68)
    tf = vtk.vtkTransformPolyDataFilter()
    tf.SetInputData(ar.GetOutput())
    tf.SetTransform(tr)
    tf.Update()
    ap = vtk.vtkPolyData()
    ap.DeepCopy(tf.GetOutput())
    An = addpoly("flecha_100N", ap)
    style(An, (1.0, 0.25, 0.1))
    reset_cam(0.95)
    orbit(5.0, 200, "Condiciones de contorno: azul = apoyo fijo (condilos) | rojo = carga de compresion 100 N")

    # ---------- D: resultados ----------
    hide_all()
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
                c = [stops[k][1][j] * (1 - u) + stops[k + 1][1][j] * u for j in range(3)]
                break
        jet.SetColor(i, "c%d" % i, c[0], c[1], c[2], 1.0)
    dn.SetAndObserveColorNodeID(jet.GetID())
    dn.SetScalarRangeFlag(slicer.vtkMRMLDisplayNode.UseManualScalarRange)
    dn.SetScalarRange(0, 2.0)
    dn.SetScalarVisibility(True)
    try:
        lg = slicer.modules.colors.logic().AddDefaultColorLegendDisplayNode(Rn)
        lg.SetTitleText("Von Mises (MPa)")
        lg.SetVisibility(True)
    except Exception as e:
        print("leyenda", e, flush=True)
    reset_cam(1.0)
    SC = 300.0

    def setwarp(t):
        wv.SetScaleFactor(SC * t)
        wv.Update()
        out.DeepCopy(wv.GetOutput())
        out.GetPointData().SetActiveScalars("von_mises_nodal_MPa")
        Rn.Modified()

    hold(1.0, "Resultados: tension de von Mises (0-2 MPa) - 100 N de compresion axial")
    orbit(2.5, 60, "Deformacion amplificada hasta x300 (desplazamiento real max ~0.1 mm)", each=setwarp)
    orbit(6.0, 300, "Von Mises: media 0.36 MPa, p99 1.4 MPa | reaccion en apoyo = 100 N | deformacion x300")
    hold(1.5, "Fin - analisis lineal estatico (E = 17 GPa, nu = 0.3) calculado con solver propio")
except Exception as e:
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
