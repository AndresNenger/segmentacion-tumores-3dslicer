import sys, time, subprocess, json, math
sys.path.append("C:/Users/Laboratorio/Downloads/femur_vh/deps_vid")
import slicer, vtk, qt, numpy as np
import imageio_ffmpeg
from vtk.util.numpy_support import vtk_to_numpy

P = "C:/Users/Laboratorio/Downloads/pelvis_guia"
B = "C:/Users/Laboratorio/Downloads/femur_vh/s016/016/SMIR.Lower_limb.095Y.F.CT.476/"
OUT = P + "/pelvis_guide_60s_EN.mp4"
FPS = 24
DT = 1.0 / FPS
H = "4.5"
res = json.load(open(P + "/fea_pelvis_h%s.json" % H))
imp = json.load(open(P + "/impresion_plan.json"))
g = np.load(P + "/guia_geom.npz")
c_a, axis = g["c_a"], g["axis"]
asis_R, asis_L, S_pt = g["asis_R"], g["asis_L"], g["S"]

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
ren = view.renderWindow().GetRenderers().GetFirstRenderer()
cam = slicer.modules.cameras.logic().GetViewActiveCameraNode(vn).GetCamera()

# ---------- CT y segmentacion experta (precarga, oculta) ----------
ctv = slicer.util.loadVolume(B + "SMIR.Lower_limb.095Y.F.CT.476.nrrd")
segE = slicer.util.loadSegmentation(B + "SMIR.Lower_limb.095Y.F.CT.476-Pelvis-Thighs_Reconstruction.seg.nrrd")
sd = segE.GetDisplayNode()
sd.SetVisibility3D(False)
sg = segE.GetSegmentation()
for i in range(sg.GetNumberOfSegments()):
    sd.SetSegmentVisibility(sg.GetNthSegmentID(i), sg.GetNthSegment(i).GetName() in ("Hip_R", "Hip_L", "Sacrum"))
sd.SetOpacity2DFill(0.45)
sd.SetVisibility(False)
for cn in slicer.util.getNodesByClass("vtkMRMLSliceCompositeNode"):
    cn.SetBackgroundVolumeID(None)
pump(5)


def addpoly(name, pd, col, op=1.0):
    n = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", name)
    n.SetAndObservePolyData(pd)
    n.CreateDefaultDisplayNodes()
    d = n.GetDisplayNode()
    d.SetColor(*col)
    d.SetOpacity(op)
    d.SetAmbient(0.25)
    d.SetDiffuse(0.8)
    d.SetSpecular(0.2)
    d.SetVisibility(False)
    return n


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


hipR = load("modelos/Hip_R.stl", (0.88, 0.35, 0.30))
hipL = load("modelos/Hip_L.stl", (0.35, 0.50, 0.88))
sac = load("modelos/Sacrum.stl", (0.30, 0.70, 0.40))
guide = load("guia_copa_acetabular.stl", (0.10, 0.75, 0.70))
cup = load("copa_referencia_48mm.stl", (0.25, 0.45, 0.95), 0.45)
rod = load("eje_planificado.stl", (1.0, 0.2, 0.15))

# marcadores pelvicos
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
mk = vtk.vtkPolyData()
mk.DeepCopy(gl.GetOutput())
markers = addpoly("markers", mk, (1.0, 0.85, 0.1))
poly = vtk.vtkPolygon()
poly.GetPointIds().SetNumberOfIds(3)
for i in range(3):
    poly.GetPointIds().SetId(i, i)
cells = vtk.vtkCellArray()
cells.InsertNextCell(poly)
tri = vtk.vtkPolyData()
tri.SetPoints(pts)
tri.SetPolys(cells)
plane = addpoly("app", tri, (1.0, 0.85, 0.1), 0.35)
plane.GetDisplayNode().SetBackfaceCulling(False)

# ---------- FEA ----------
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
meshN = addpoly("mesh", half, (0.85, 0.85, 0.9))
meshN.GetDisplayNode().SetEdgeVisibility(True)
meshN.GetDisplayNode().SetEdgeColor(0.15, 0.25, 0.45)
sf = vtk.vtkGeometryFilter()
sf.SetInputData(ug)
sf.Update()
sp = vtk.vtkPolyData()
sp.DeepCopy(sf.GetOutput())
surfN = addpoly("surface", sp, (0.9, 0.88, 0.8), 0.45)
bc = np.load(P + "/fea_bc_h%s.npz" % H)
fixed, load_idx, head = bc["fixed"], bc["load"], bc["head"]


def spheres(idx, r, color, name):
    pp = vtk.vtkPoints()
    for i in idx:
        pp.InsertNextPoint(*X[i])
    pdx = vtk.vtkPolyData()
    pdx.SetPoints(pp)
    s = vtk.vtkSphereSource()
    s.SetRadius(r)
    s.SetThetaResolution(10)
    s.SetPhiResolution(10)
    gg = vtk.vtkGlyph3D()
    gg.SetInputData(pdx)
    gg.SetSourceConnection(s.GetOutputPort())
    gg.ScalingOff()
    gg.Update()
    o = vtk.vtkPolyData()
    o.DeepCopy(gg.GetOutput())
    return addpoly(name, o, color)


fixN = spheres(fixed, 2.4, (0.15, 0.35, 1.0), "fixed")
loadN = spheres(load_idx, 2.4, (1.0, 0.2, 0.1), "load")
Fv = np.array(res["fuerza_resultante_N"])
dv = Fv / np.linalg.norm(Fv)
ar = vtk.vtkArrowSource()
ar.SetTipResolution(24)
ar.SetShaftResolution(24)
ar.Update()
tail = head - dv * 120.0
ax_ = np.cross([1, 0, 0], dv)
ang = math.degrees(math.acos(float(np.dot([1, 0, 0], dv))))
tr = vtk.vtkTransform()
tr.Translate(*tail)
tr.RotateWXYZ(ang, *ax_)
tr.Scale(105, 105, 105)
tfa = vtk.vtkTransformPolyDataFilter()
tfa.SetInputData(ar.GetOutput())
tfa.SetTransform(tr)
tfa.Update()
ap = vtk.vtkPolyData()
ap.DeepCopy(tfa.GetOutput())
arrowN = addpoly("arrow", ap, (1.0, 0.25, 0.1))

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
outp = vtk.vtkPolyData()
outp.DeepCopy(wv.GetOutput())
resN = addpoly("result", outp, (1, 1, 1))
dn = resN.GetDisplayNode()
dn.SetActiveScalarName("von_mises_nodal_MPa")
dn.SetActiveAttributeLocation(vtk.vtkAssignAttribute.POINT_DATA)
jet = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLColorTableNode", "BlueToRed")
jet.SetTypeToUser()
jet.SetNumberOfColors(256)
stops = [(0.0, (0.0, 0.0, 0.8)), (0.25, (0.0, 0.6, 1.0)), (0.5, (0.0, 0.9, 0.2)), (0.75, (1.0, 0.9, 0.0)), (1.0, (1.0, 0.0, 0.0))]
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
lg = slicer.modules.colors.logic().AddDefaultColorLegendDisplayNode(resN)
lg.SetTitleText("Von Mises stress (MPa)")
lg.SetVisibility(False)
SC = 4.0


def setwarp(t):
    wv.SetScaleFactor(SC * t)
    wv.Update()
    outp.DeepCopy(wv.GetOutput())
    outp.GetPointData().SetActiveScalars("von_mises_nodal_MPa")
    resN.Modified()


# ---------- preparacion de impresion ----------
def read_vtp(fn):
    r = vtk.vtkXMLPolyDataReader()
    r.SetFileName(fn)
    r.Update()
    o = vtk.vtkPolyData()
    o.DeepCopy(r.GetOutput())
    return o


ct2 = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLColorTableNode", "overhang")
ct2.SetTypeToUser()
ct2.SetNumberOfColors(256)
for i in range(256):
    if i < 128:
        ct2.SetColor(i, "g%d" % i, 0.86, 0.86, 0.80, 1.0)
    else:
        ct2.SetColor(i, "r%d" % i, 1.0, 0.15, 0.10, 1.0)


def part(name, fn):
    n = addpoly(name, read_vtp(fn), (1, 1, 1))
    d = n.GetDisplayNode()
    d.SetActiveScalarName("voladizo")
    d.SetActiveAttributeLocation(vtk.vtkAssignAttribute.CELL_DATA)
    d.SetAndObserveColorNodeID(ct2.GetID())
    d.SetScalarRangeFlag(slicer.vtkMRMLDisplayNode.UseManualScalarRange)
    d.SetScalarRange(0, 1)
    d.SetScalarVisibility(True)
    return n


pGuide = part("print_guide", P + "/imprimir_guia_voladizos.vtp")
pRepl = part("print_replica", P + "/imprimir_replica_voladizos.vtp")
cube = vtk.vtkCubeSource()
cube.SetBounds(-110, 110, -110, 110, -3, 0)
cube.Update()
cp = vtk.vtkPolyData()
cp.DeepCopy(cube.GetOutput())
bed = addpoly("bed", cp, (0.38, 0.42, 0.48), 1.0)

slicer.util.selectModule("Models")
pump(5)
title = mw.windowTitle
print("TITLE", title, flush=True)

# ---------- subtitulos y tarjeta final ----------
lbl = qt.QLabel(mw)
lbl.setAttribute(qt.Qt.WA_TransparentForMouseEvents)
lbl.setStyleSheet("background-color: rgba(0,0,0,185); color: white; padding: 8px 18px;")
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


def set_view(focal, direction, dist, up=(0, 0, 1)):
    d = np.array(direction, float)
    d /= np.linalg.norm(d)
    cam.SetFocalPoint(*focal)
    cam.SetPosition(*(np.array(focal) + d * dist))
    cam.SetViewUp(*up)
    ren.ResetCameraClippingRange()


def vis(nodes, on=True):
    for n in nodes:
        n.GetDisplayNode().SetVisibility(on)


ALL = [hipR, hipL, sac, guide, cup, rod, markers, plane, meshN, surfN, fixN, loadN, arrowN, resN, pGuide, pRepl, bed]


def only(nodes, ops=None):
    vis(ALL, False)
    for n in nodes:
        n.GetDisplayNode().SetVisibility(True)
        n.GetDisplayNode().SetOpacity((ops or {}).get(n.GetName(), 1.0))
    lg.SetVisibility(False)


def fade_in(node, sec, final=1.0):
    d = node.GetDisplayNode()
    d.SetOpacity(0.0)
    d.SetVisibility(True)
    n = max(int(sec * FPS), 1)
    for i in range(1, n + 1):
        d.SetOpacity(final * i / n)
        tick()


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


def orbit(sec, deg, each=None):
    n = int(sec * FPS)
    a = np.radians(deg / n)
    ca, sa = np.cos(a), np.sin(a)
    for i in range(n):
        f = np.array(cam.GetFocalPoint())
        p = np.array(cam.GetPosition()) - f
        p = np.array([ca * p[0] - sa * p[1], sa * p[0] + ca * p[1], p[2]])
        cam.SetPosition(*(f + p))
        cam.SetViewUp(0, 0, 1)
        if each:
            each(i / (n - 1 if n > 1 else 1))
        tick()


# --- estado inicial (escena 0: gancho) ---
focal = c_a + axis * 22.0
only([hipR, hipL, sac, guide, cup, rod], {"Hip_L": 0.3, "Sacrum": 0.3, "copa_referencia_48mm": 0.45, "Hip_R": 1.0})
hipR.GetDisplayNode().SetColor(0.90, 0.88, 0.82)
hipL.GetDisplayNode().SetColor(0.80, 0.80, 0.78)
sac.GetDisplayNode().SetColor(0.80, 0.80, 0.78)
set_view(focal, (0.7, 0.7, 0.35), 250)
cap("From a CT scan to a 3D-printed surgical guide", "Engineering + biomedicine · academic project")
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
state["next"] = time.time()
tstart = time.time()

try:
    # S0 (0-4 s)
    orbit(4.0, 100)

    # S1 (4-11 s): CT + segmentacion
    lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
    pump(8)
    for cn in slicer.util.getNodesByClass("vtkMRMLSliceCompositeNode"):
        cn.SetBackgroundVolumeID(ctv.GetID())
    sd.SetVisibility(True)
    slicer.modules.markups.logic().JumpSlicesToLocation(float(head[0]), float(head[1]), float(head[2]) + 10, True)
    slicer.util.resetSliceViews()
    slicer.modules.markups.logic().JumpSlicesToLocation(float(head[0]), float(head[1]), float(head[2]) + 10, True)
    only([hipR, hipL, sac])
    hipR.GetDisplayNode().SetColor(0.88, 0.35, 0.30)
    hipL.GetDisplayNode().SetColor(0.35, 0.50, 0.88)
    sac.GetDisplayNode().SetColor(0.30, 0.70, 0.40)
    pc = (np.array(hipR.GetPolyData().GetCenter()) + np.array(hipL.GetPolyData().GetCenter())) / 2
    set_view(pc, (0, 1, 0.1), 650)
    cap("1 · Segment the pelvis from a real CT", "3D Slicer · sacrum and both hip bones in axial, coronal and sagittal views")
    orbit(7.0, 60)

    # S2 (11-16 s): modelos 3D limpios
    lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUp3DView)
    pump(8)
    sd.SetVisibility(False)
    set_view(pc, (0, 1, 0.1), 560)
    cap("2 · Clean 3D bone models", "Single island · holes filled · smoothed · closed meshes")
    orbit(5.0, 200)

    # S3 (16-20 s): malla FEA
    only([meshN])
    fc = np.array(ug.GetCenter())
    set_view(fc, (1, 0.3, 0.15), 380)
    cap("3 · Finite element analysis", "%d tetrahedra · cortical bone (E = 17 GPa, ν = 0.3)" % ug.GetNumberOfCells())
    orbit(4.0, 160)

    # S4 (20-25 s): condiciones de contorno
    only([surfN, fixN, loadN, arrowN], {"surface": 0.45})
    set_view(fc, (1, 0.3, 0.15), 380)
    cap("Boundary conditions", "Blue: fixed (sacroiliac joint + pubic symphysis) · Red: 200 kN load on the acetabular roof")
    orbit(5.0, 200)

    # S5 (25-33 s): resultados
    only([resN])
    lg.SetVisibility(True)
    set_view(fc, (1, 0.3, 0.15), 380)
    cap("Result at 200 kN (extreme case)", "Red = above the strength of cortical bone (~130 MPa)")
    hold(1.0)
    cap("Deformation exaggerated ×4", "Maximum displacement: %.1f mm" % res["u_max_mm"])
    orbit(2.5, 40, each=setwarp)
    cap("The bone would fail: %.0f %% of its volume exceeds 130 MPa" % (100 * res["fraccion_volumen_sobre_130MPa"]),
        "Normal hip loads are only ~2–6 kN (linear simulation)")
    orbit(4.5, 160)

    # S6 (33-36 s): plano pelvico
    only([hipR, hipL, sac, markers, plane], {"anterior_pelvic": 1.0, "app": 0.35})
    hipR.GetDisplayNode().SetColor(0.90, 0.88, 0.82)
    hipL.GetDisplayNode().SetColor(0.85, 0.85, 0.82)
    sac.GetDisplayNode().SetColor(0.85, 0.85, 0.82)
    plane.GetDisplayNode().SetOpacity(0.35)
    set_view(pc, (0, 1, 0.1), 560)
    cap("4 · Plan the cup orientation", "Anterior pelvic plane → 40° inclination · 15° anteversion")
    orbit(3.0, 30)

    # S7 (36-39 s): eje y copa
    only([hipR, hipL, sac, rod, cup], {"Hip_L": 0.3, "Sacrum": 0.3, "copa_referencia_48mm": 0.45})
    set_view(focal, (0.7, 0.7, 0.35), 250)
    cap("Planned cup axis", "48 mm cup placed in the acetabulum")
    orbit(3.0, 60)

    # S8 (39-47 s): guia
    cap("5 · Design the guide", "3 contact patches that copy the bone + a tube aligned with the cup axis")
    fade_in(guide, 1.0)
    orbit(4.0, 150)
    cap("View along the cup axis", "The guide bore is concentric with the cup")
    d_axis = np.array(axis, float)
    f0, p0 = np.array(cam.GetFocalPoint()), np.array(cam.GetPosition())
    v0 = (p0 - f0) / np.linalg.norm(p0 - f0)
    n = int(3.0 * FPS)
    for i in range(1, n + 1):
        s = i / n
        s = s * s * (3 - 2 * s)
        v = v0 * (1 - s) + d_axis * s
        v /= np.linalg.norm(v)
        cam.SetPosition(*(focal + v * (250 * (1 - s) + 260 * s)))
        cam.SetFocalPoint(*focal)
        cam.SetViewUp(0, 0, 1)
        tick()

    # S9 (47-53 s): preparacion de impresion
    only([bed, pGuide, pRepl])
    set_view((0, 0, 45), (0, -1, 0.55), 360)
    cap("6 · Prepare it for 3D printing", "Oriented, watertight meshes · bone replica to test the fit · ≈ 2 h print (Creality K1C estimate)")
    orbit(6.0, 140)

    # S10 (53-60 s): tarjeta final
    html = ("<div style='font-size:22px; color:#f2c94c; font-weight:bold; margin-bottom:8px'>ENGINEERING + BIOMEDICINE</div>"
            "<div style='font-size:46px; font-weight:bold; margin-bottom:26px'>CT scan → simulation → surgical-guide concept → 3D print</div>"
            "<div style='font-size:27px; margin-bottom:14px'>An academic exercise with cadaver data.</div>"
            "<div style='font-size:27px; margin-bottom:14px'><b>Not a medical device. Not for clinical use.</b></div>"
            "<div style='font-size:20px; color:#9fb3d1; margin-top:20px'>Data: Fischer, Sci Data 2023 (CC BY-NC-SA) · Tools: 3D Slicer, Python, OrcaSlicer</div>")
    card.setText(html)
    card.setGeometry(0, 0, mw.width, mw.height)
    card.show()
    card.raise_()
    lbl.hide()
    hold(7.0)
except Exception:
    import traceback
    print("ERROR", traceback.format_exc(), flush=True)
finally:
    print("DURACION_s", round(time.time() - tstart, 1), flush=True)
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
