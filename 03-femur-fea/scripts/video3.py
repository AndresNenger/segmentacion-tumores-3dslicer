import sys, time
sys.path.append("C:/Users/Laboratorio/Downloads/femur_vh/deps_vid")
import slicer, vtk, qt, numpy as np
import imageio
from vtk.util.numpy_support import vtk_to_numpy
from PIL import Image, ImageDraw, ImageFont

d = "C:/Users/Laboratorio/Downloads/femur_vh"
W, H, FPS = 1280, 720, 24
font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 34)
writer = imageio.get_writer(d + "/femur_redes_30s.mp4", fps=FPS, codec="libx264", quality=8,
                            macro_block_size=None, pixelformat="yuv420p")
nframes = [0]
mw = slicer.util.mainWindow()
mw.showMaximized()
for _f in (lambda: mw.findChild(qt.QDockWidget, "PanelDockWidget").setVisible(False),
           lambda: slicer.util.setDataProbeVisible(False),
           lambda: slicer.util.setToolbarsVisible(False)):
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
renderer = view.renderWindow().GetRenderers().GetFirstRenderer()


def pump(n=3):
    for _ in range(n):
        slicer.app.processEvents()


def grab():
    view.forceRender()
    pump(2)
    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(view.renderWindow())
    w2i.SetInputBufferTypeToRGB()
    w2i.ReadFrontBufferOff()
    w2i.Update()
    im = w2i.GetOutput()
    dims = im.GetDimensions()
    a = vtk_to_numpy(im.GetPointData().GetScalars()).reshape(dims[1], dims[0], 3)[::-1]
    return Image.fromarray(a.copy())


def wrap(draw, text, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def frame(caption):
    img = grab()
    iw, ih = img.size
    s = min(W / iw, H / ih)
    img = img.resize((int(iw * s), int(ih * s)), Image.LANCZOS)
    canvas = Image.new("RGB", (W, H), (13, 15, 26))
    canvas.paste(img, ((W - img.width) // 2, (H - img.height) // 2))
    tmp = ImageDraw.Draw(canvas)
    lines = wrap(tmp, caption, W - 70)
    bar_h = 28 + 44 * len(lines)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(ov).rectangle([0, H - bar_h, W, H], fill=(0, 0, 0, 185))
    canvas = Image.alpha_composite(canvas.convert("RGBA"), ov).convert("RGB")
    dr = ImageDraw.Draw(canvas)
    y = H - bar_h + 14
    for ln in lines:
        dr.text((35, y), ln, font=font, fill=(255, 255, 255))
        y += 44
    writer.append_data(np.asarray(canvas))
    nframes[0] += 1


def cam():
    return slicer.modules.cameras.logic().GetViewActiveCameraNode(vn).GetCamera()


def orbit(n, deg, cap, each=None):
    for i in range(n):
        cam().Azimuth(deg / n)
        cam().OrthogonalizeViewUp()
        renderer.ResetCameraClippingRange()
        if each:
            each(i / (n - 1 if n > 1 else 1))
        frame(cap)


def reset_cam(zoom=1.0):
    slicer.util.resetThreeDViews()
    c = cam()
    fp = c.GetFocalPoint()
    dist = c.GetDistance()
    c.SetPosition(fp[0], fp[1] + dist, fp[2])
    c.SetViewUp(0, 0, 1)
    c.Zoom(zoom * 0.8)
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


# ---- Escena 1 (0-5 s): fémures girando ----
Lm = slicer.util.loadModel(d + "/s016/016/Models/Femur_L.ply")
style(Lm, (0.93, 0.88, 0.75))
Rm = slicer.util.loadModel(d + "/s016/016/Models/Femur_R.ply")
style(Rm, (0.72, 0.86, 0.93))
reset_cam(1.0)
orbit(5 * FPS, 360, "¿Cuánto peso aguanta tu hueso más grande? Lo probamos… en computadora.")

# ---- Escena 2 (5-12 s): malla ----
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
orbit(7 * FPS, 200, "Con una tomografía armamos este fémur en 3D y lo dividimos en miles de piececitas. Eso se llama elementos finitos.")

# ---- Escena 3 (12-19 s): apoyo y carga ----
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


spheres(fixed, 1.8, (0.15, 0.35, 1.0), "apoyo_fijo")
spheres(pa, 1.8, (1.0, 0.2, 0.1), "zona_carga")
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
orbit(7 * FPS, 200, "Lo apoyamos abajo y le pusimos encima 100 newtons. Es como un paquete de 10 kilos sobre la cadera.")

# ---- Escena 4 (19-25 s): tensiones ----
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
    lg.SetTitleText("Tensión (MPa)")
    lg.SetVisibility(True)
except Exception as e:
    print("leyenda", e, flush=True)
reset_cam(1.0)
SC = 300.0


def setwarp(t):
    f = min(1.0, t / 0.4)
    wv.SetScaleFactor(SC * f)
    wv.Update()
    out.DeepCopy(wv.GetOutput())
    out.GetPointData().SetActiveScalars("von_mises_nodal_MPa")
    Rn.Modified()


orbit(6 * FPS, 120, "¿Resultado? Casi todo azul: el hueso ni sudó. Se hunde menos que un cabello.", each=setwarp)

# ---- Escena 5 (25-30 s): cierre ----
orbit(5 * FPS, 150, "Para romperlo hacen falta cientos de kilos… o una caída mala si el hueso está débil. Cuida tus huesos.",
      each=lambda t: None)
writer.close()
print("VIDEO_DONE", nframes[0], flush=True)
slicer.app.quit()
