import sys, math, time
sys.path.append("C:/Users/Laboratorio/Downloads/femur_vh/deps_vid")
import slicer, vtk, qt, numpy as np
import imageio
from vtk.util.numpy_support import vtk_to_numpy
from PIL import Image, ImageDraw, ImageFont
d = "C:/Users/Laboratorio/Downloads/femur_vh"
W, H, FPS = 1280, 720, 24
font = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 30)
font2 = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 22)
writer = imageio.get_writer(d + "/femur_slicer_FEA.mp4", fps=FPS, codec="libx264", quality=8,
                            macro_block_size=None, pixelformat="yuv420p")
nframes = [0]
mw = slicer.util.mainWindow()
mw.showMaximized()
for _f in (lambda: mw.findChild(qt.QDockWidget, "PanelDockWidget").setVisible(False), lambda: slicer.util.setDataProbeVisible(False), lambda: slicer.util.setToolbarsVisible(False)):
    try:
        _f()
    except Exception as _e:
        print("ui", _e, flush=True)
slicer.app.layoutManager().setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUp3DView)
tw = slicer.app.layoutManager().threeDWidget(0)
view = tw.threeDView()
vn = view.mrmlViewNode()
vn.SetBackgroundColor(0.05, 0.06, 0.10)
vn.SetBackgroundColor2(0.20, 0.22, 0.30)
vn.SetBoxVisible(False)
vn.SetAxisLabelsVisible(False)


def pump(n=3):
    for _ in range(n):
        slicer.app.processEvents()


def grab():
    view.forceRender()
    pump(2)
    rw = view.renderWindow()
    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(rw)
    w2i.SetInputBufferTypeToRGB()
    w2i.ReadFrontBufferOff()
    w2i.Update()
    im = w2i.GetOutput()
    dims = im.GetDimensions()
    a = vtk_to_numpy(im.GetPointData().GetScalars()).reshape(dims[1], dims[0], 3)[::-1]
    return Image.fromarray(a.copy())


def frame(caption, sub=""):
    img = grab()
    iw, ih = img.size
    s = min(W / iw, H / ih)
    img = img.resize((int(iw * s), int(ih * s)), Image.LANCZOS)
    canvas = Image.new("RGB", (W, H), (13, 15, 26))
    canvas.paste(img, ((W - img.width) // 2, (H - img.height) // 2))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(ov)
    dr.rectangle([0, H - 92, W, H], fill=(0, 0, 0, 170))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), ov).convert("RGB")
    dr = ImageDraw.Draw(canvas)
    dr.text((28, H - 84), caption, font=font, fill=(255, 255, 255))
    if sub:
        dr.text((28, H - 40), sub, font=font2, fill=(190, 200, 220))
    writer.append_data(np.asarray(canvas))
    nframes[0] += 1


def cam():
    return slicer.modules.cameras.logic().GetViewActiveCameraNode(vn).GetCamera()


def orbit(n, deg, cap, sub="", each=None):
    for i in range(n):
        cam().Azimuth(deg / n)
        cam().OrthogonalizeViewUp()
        view.renderWindow().GetRenderers().GetFirstRenderer().ResetCameraClippingRange()
        if each:
            each(i / (n - 1 if n > 1 else 1))
        frame(cap, sub)


def hold(n, cap, sub=""):
    for _ in range(n):
        frame(cap, sub)


def reset_cam(zoom=1.0):
    slicer.util.resetThreeDViews()
    c = cam()
    fp = c.GetFocalPoint()
    dist = c.GetDistance()
    c.SetPosition(fp[0], fp[1] + dist, fp[2])
    c.SetViewUp(0, 0, 1)
    c.Zoom(zoom * 0.85)
    view.renderWindow().GetRenderers().GetFirstRenderer().ResetCameraClippingRange()
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


# ---------- Escena A: apertura y carga ----------
hold(FPS, "3D Slicer", "Abriendo la aplicación…")
Lm = slicer.util.loadModel(d + "/s016/016/Models/Femur_L.ply")
style(Lm, (0.93, 0.88, 0.75))
reset_cam(1.0)
hold(FPS, "Carga del modelo: fémur izquierdo", "Segmentación del CT postmortem (malla de ~600 000 triángulos)")
Rm = slicer.util.loadModel(d + "/s016/016/Models/Femur_R.ply")
style(Rm, (0.72, 0.86, 0.93))
reset_cam(1.0)
hold(FPS, "Carga del modelo: fémur derecho", "Ambos fémures en escala real (~392 mm)")
orbit(120, 360, "Fémures izquierdo y derecho", "Vista 3D en 3D Slicer")

# ---------- Escena B: malla FEA ----------
rd = vtk.vtkXMLUnstructuredGridReader()
rd.SetFileName(d + "/fea_femur_L_h3.5.vtu")
rd.Update()
ug = rd.GetOutput()
X = vtk_to_numpy(ug.GetPoints().GetData())
print("UG", ug.GetNumberOfPoints(), ug.GetNumberOfCells(), flush=True)
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
orbit(96, 200, "Modelo de elementos finitos (fémur izquierdo)",
      "Malla de tetraedros lineales: %d nodos · %d elementos · corte para ver el interior"
      % (ug.GetNumberOfPoints(), ug.GetNumberOfCells()))

# ---------- Escena C: condiciones de contorno ----------
hide_all()
surf = vtk.vtkGeometryFilter()
surf.SetInputData(ug)
surf.Update()
sp = vtk.vtkPolyData()
sp.DeepCopy(surf.GetOutput())
Sn = addpoly("superficie_FEA", sp)
style(Sn, (0.9, 0.88, 0.8), 0.45)
zmin, zmax = X[:, 2].min(), X[:, 2].max()
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
    return n


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
txt = vtk.vtkVectorText()
txt.SetText("F = 100 N")
txt.Update()
tt = vtk.vtkTransform()
tt.Translate(X[top][0] + 25, X[top][1], X[top][2] + 85)
tt.RotateX(90)
tt.Scale(9, 9, 9)
tfx = vtk.vtkTransformPolyDataFilter()
tfx.SetInputConnection(txt.GetOutputPort())
tfx.SetTransform(tt)
tfx.Update()
tp = vtk.vtkPolyData()
tp.DeepCopy(tfx.GetOutput())
Tn = addpoly("etiqueta_F", tp)
style(Tn, (1, 1, 1))
reset_cam(0.95)
orbit(110, 200, "Condiciones de contorno",
      "Azul: apoyo fijo en cóndilos (4 mm inferiores) · Rojo: carga de compresión de 100 N en la cabeza femoral")

# ---------- Escena D: resultados ----------
hide_all()
ug2 = vtk.vtkUnstructuredGrid()
ug2.ShallowCopy(ug)
g2 = vtk.vtkGeometryFilter()
g2.SetInputData(ug2)
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
stops = [(0.0, (0.0, 0.0, 0.8)), (0.25, (0.0, 0.6, 1.0)), (0.5, (0.0, 0.9, 0.2)), (0.75, (1.0, 0.9, 0.0)), (1.0, (1.0, 0.0, 0.0))]
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


hold(12, "Resultados: tensión de von Mises", "Fémur izquierdo · 100 N de compresión axial · E = 17 GPa, ν = 0.3")
orbit(48, 60, "Resultados: deformación ampliada", "Desplazamiento amplificado hasta ×300 (real máx. ≈ 0.1 mm)", each=setwarp)
orbit(120, 300, "Resultados: tensión de von Mises",
      "Media 0.36 MPa · p99 1.4 MPa · reacción en el apoyo = 100 N · deformación ×300")
hold(36, "Fin del análisis en 3D Slicer",
     "Elementos finitos lineales estáticos · solver propio (scipy) · escala de color 0–2 MPa")
writer.close()
print("VIDEO_DONE", nframes[0], flush=True)
slicer.app.quit()
