import sys, time, subprocess, json, math
sys.path.append("C:/Users/Laboratorio/Downloads/femur_vh/deps_vid")
import slicer, vtk, qt, numpy as np
import imageio_ffmpeg

P = "C:/Users/Laboratorio/Downloads/pelvis_guia"
OUT = P + "/segmento_guia.mp4"
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

lm = slicer.app.layoutManager()
lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUp3DView)
pump(5)
view = lm.threeDWidget(0).threeDView()
vn = view.mrmlViewNode()
vn.SetBoxVisible(False)
vn.SetAxisLabelsVisible(False)
vn.SetBackgroundColor(0.05, 0.06, 0.10)
vn.SetBackgroundColor2(0.20, 0.26, 0.34)
rw = view.renderWindow()
ren = rw.GetRenderers().GetFirstRenderer()
cam = slicer.modules.cameras.logic().GetViewActiveCameraNode(vn).GetCamera()

g = np.load(P + "/guia_geom.npz")
c_a, axis = g["c_a"], g["axis"]
asis_R, asis_L, S_pt = g["asis_R"], g["asis_L"], g["S"]


def load(fn, col, op=1.0):
    m = slicer.util.loadNodeFromFile(P + "/" + fn, "ModelFile", {"coordinateSystem": "RAS"})
    d = m.GetDisplayNode()
    d.SetColor(*col)
    d.SetOpacity(op)
    d.SetAmbient(0.25)
    d.SetDiffuse(0.8)
    d.SetSpecular(0.25)
    d.SetVisibility(False)
    return m


def addpoly(name, pd, col, op=1.0):
    n = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", name)
    n.SetAndObservePolyData(pd)
    n.CreateDefaultDisplayNodes()
    d = n.GetDisplayNode()
    d.SetColor(*col)
    d.SetOpacity(op)
    d.SetVisibility(False)
    return n


hipR = load("modelos/Hip_R.stl", (0.90, 0.88, 0.82))
hipL = load("modelos/Hip_L.stl", (0.80, 0.80, 0.78))
sac = load("modelos/Sacrum.stl", (0.80, 0.80, 0.78))
guide = load("guia_copa_acetabular.stl", (0.10, 0.75, 0.70))
cup = load("copa_referencia_48mm.stl", (0.25, 0.45, 0.95), 0.45)
rod = load("eje_planificado.stl", (1.0, 0.2, 0.15))

# marcadores pelvicos y plano pelvico anterior
pts = vtk.vtkPoints()
for p in (asis_R, asis_L, S_pt):
    pts.InsertNextPoint(*p)
pd = vtk.vtkPolyData()
pd.SetPoints(pts)
sph = vtk.vtkSphereSource()
sph.SetRadius(6)
sph.SetThetaResolution(16)
sph.SetPhiResolution(16)
gl = vtk.vtkGlyph3D()
gl.SetInputData(pd)
gl.SetSourceConnection(sph.GetOutputPort())
gl.ScalingOff()
gl.Update()
mk_pd = vtk.vtkPolyData()
mk_pd.DeepCopy(gl.GetOutput())
markers = addpoly("marcadores_pelvicos", mk_pd, (1.0, 0.85, 0.1))
poly = vtk.vtkPolygon()
poly.GetPointIds().SetNumberOfIds(3)
for i in range(3):
    poly.GetPointIds().SetId(i, i)
cells = vtk.vtkCellArray()
cells.InsertNextCell(poly)
tri_pd = vtk.vtkPolyData()
tri_pd.SetPoints(pts)
tri_pd.SetPolys(cells)
app_plane = addpoly("plano_pelvico_anterior", tri_pd, (1.0, 0.85, 0.1), 0.35)
app_plane.GetDisplayNode().SetBackfaceCulling(False)

b = [0.0] * 6
bb = np.array([hipR.GetPolyData().GetBounds(), hipL.GetPolyData().GetBounds(), sac.GetPolyData().GetBounds()])
pel_c = np.array([(bb[:, 0].min() + bb[:, 1].max()) / 2, (bb[:, 2].min() + bb[:, 3].max()) / 2, (bb[:, 4].min() + bb[:, 5].max()) / 2])

slicer.util.selectModule("Models")
pump(5)
title = mw.windowTitle
print("TITLE", title, flush=True)

lbl = qt.QLabel(mw)
lbl.setAttribute(qt.Qt.WA_TransparentForMouseEvents)
lbl.setStyleSheet("background-color: rgba(0,0,0,185); color: white; padding: 8px 18px;")


def cap(a, b2=""):
    lbl.setText("<div style='font-size:24px;font-weight:bold'>%s</div><div style='font-size:16px;color:#c8d6f0'>%s</div>" % (a, b2))
    lbl.setGeometry(0, mw.height - 120, mw.width, 96)
    lbl.show()
    lbl.raise_()


def set_view(focal, direction, dist, up=(0, 0, 1)):
    d = np.array(direction, float)
    d /= np.linalg.norm(d)
    cam.SetFocalPoint(*focal)
    cam.SetPosition(*(np.array(focal) + d * dist))
    cam.SetViewUp(*up)
    ren.ResetCameraClippingRange()


set_view(pel_c, (0, 1, 0.1), 600)
hipR.GetDisplayNode().SetVisibility(True)
hipL.GetDisplayNode().SetVisibility(True)
sac.GetDisplayNode().SetVisibility(True)
cap("Paso 7: de la simulación a la guía quirúrgica académica", "Orientar la copa acetabular del coxal derecho")
ren.ResetCameraClippingRange()
pump(10)
view.forceRender()
pump(10)

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


def tick():
    ren.ResetCameraClippingRange()
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


def hold(sec):
    for _ in range(int(sec * FPS)):
        tick()


def orbit(sec, deg):
    n = int(sec * FPS)
    for _ in range(n):
        cam.Azimuth(deg / n)
        cam.OrthogonalizeViewUp()
        ren.ResetCameraClippingRange()
        tick()


def move_to(focal1, dir1, dist1, sec, up=(0, 0, 1)):
    f0 = np.array(cam.GetFocalPoint())
    p0 = np.array(cam.GetPosition())
    d0 = np.linalg.norm(p0 - f0)
    v0 = (p0 - f0) / d0
    v1 = np.array(dir1, float)
    v1 /= np.linalg.norm(v1)
    n = int(sec * FPS)
    for i in range(1, n + 1):
        s = i / n
        s = s * s * (3 - 2 * s)
        f = f0 * (1 - s) + np.array(focal1) * s
        v = v0 * (1 - s) + v1 * s
        v /= np.linalg.norm(v)
        d = d0 * (1 - s) + dist1 * s
        cam.SetFocalPoint(*f)
        cam.SetPosition(*(f + v * d))
        cam.SetViewUp(*up)
        ren.ResetCameraClippingRange()
        tick()


def fade_in(node, sec, final=1.0):
    dn = node.GetDisplayNode()
    dn.SetOpacity(0.0)
    dn.SetVisibility(True)
    n = max(int(sec * FPS), 1)
    for i in range(1, n + 1):
        dn.SetOpacity(final * i / n)
        tick()


try:
    hold(2.0)
    # --- marcadores y plano pelvico ---
    cap("Planificación: plano pélvico anterior", "Espinas ilíacas anterosuperiores (ASIS) y sínfisis púbica · marcadores detectados de forma automática y aproximada")
    markers.GetDisplayNode().SetVisibility(True)
    fade_in(app_plane, 1.0, 0.35)
    orbit(4.0, 30)
    # --- eje y copa ---
    app_plane.GetDisplayNode().SetVisibility(False)
    markers.GetDisplayNode().SetVisibility(False)
    hipL.GetDisplayNode().SetOpacity(0.30)
    sac.GetDisplayNode().SetOpacity(0.30)
    focal = c_a + axis * 22.0
    cap("Eje de la copa acetabular", "Inclinación 40° · anteversión 15° (zona de Lewinnek) · copa de 48 mm")
    move_to(focal, (0.7, 0.7, 0.35), 250, 2.5)
    fade_in(cup, 0.8, 0.45)
    rod.GetDisplayNode().SetVisibility(True)
    orbit(4.0, 90)
    # --- guia ---
    cap("Guía quirúrgica académica", "3 parches de contacto que copian el hueso · tubo guía alineado con el eje · orificios para clavijas")
    fade_in(guide, 1.2, 1.0)
    orbit(8.0, 210)
    # --- vista a lo largo del eje ---
    cap("Vista a lo largo del eje de la copa", "El orificio de la guía (Ø 9,2 mm) queda concéntrico con la copa: por él pasaría una aguja de ≤ 4 mm hasta la pared medial")
    d_axis = tuple(axis)
    move_to(focal, d_axis, 260, 2.8)
    hold(4.5)
    cap("Aviso: ejercicio académico con datos de un cadáver", "No es un dispositivo médico ni apto para uso clínico · validación y planificación médica obligatorias")
    orbit(4.5, 60)
    hold(1.0)
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
