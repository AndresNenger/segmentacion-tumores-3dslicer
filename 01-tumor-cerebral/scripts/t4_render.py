import time, traceback
import slicer, vtk, numpy as np
from vtk.util.numpy_support import vtk_to_numpy
from PIL import Image, ImageDraw, ImageFont

P = "C:/Users/Laboratorio/Downloads/tumor_cerebral"
mw = slicer.util.mainWindow()
mw.showMaximized()


def pump(n=5):
    for _ in range(n):
        slicer.app.processEvents()


try:
    t0 = time.time()
    while time.time() - t0 < 3:
        pump()
    lm = slicer.app.layoutManager()
    lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUp3DView)
    pump()
    view = lm.threeDWidget(0).threeDView()
    vn = view.mrmlViewNode()
    vn.SetBoxVisible(False); vn.SetAxisLabelsVisible(False)
    vn.SetBackgroundColor(0.05, 0.06, 0.10); vn.SetBackgroundColor2(0.22, 0.28, 0.36)
    g = np.load(P + "/plan_geom.npz")
    c_t, entry, d = g["c_t"], g["entry"], g["d"]

    def load(fn, col, op=1.0):
        m = slicer.util.loadNodeFromFile(P + "/" + fn, "ModelFile", {"coordinateSystem": "RAS"})
        dn = m.GetDisplayNode(); dn.SetColor(*col); dn.SetOpacity(op)
        dn.SetAmbient(0.25); dn.SetDiffuse(0.8); dn.SetSpecular(0.25)
        return m

    skin = load("piel.stl", (0.93, 0.78, 0.68), 0.35)
    tum = load("tumor_modelo.stl", (1.0, 0.82, 0.1))
    tpl = load("plantilla_craneotomia.stl", (0.10, 0.75, 0.70))
    out = load("contorno_craneotomia.stl", (1.0, 0.15, 0.15))
    tra = load("trayectoria.stl", (1.0, 0.35, 0.1))
    pump(10)
    rw = view.renderWindow(); ren = rw.GetRenderers().GetFirstRenderer()
    cam = slicer.modules.cameras.logic().GetViewActiveCameraNode(vn).GetCamera()
    font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 30)

    def shot(name, focal, direction, dist, title, up=(0, 0, 1)):
        dd = np.array(direction, float); dd /= np.linalg.norm(dd)
        cam.SetFocalPoint(*focal); cam.SetPosition(*(np.array(focal) + dd * dist)); cam.SetViewUp(*up)
        ren.ResetCameraClippingRange(); pump(8); view.forceRender()
        w2i = vtk.vtkWindowToImageFilter(); w2i.SetInput(rw); w2i.SetInputBufferTypeToRGB(); w2i.ReadFrontBufferOff(); w2i.Update()
        im = w2i.GetOutput(); dims = im.GetDimensions()
        a = vtk_to_numpy(im.GetPointData().GetScalars()).reshape(dims[1], dims[0], 3)[::-1]
        img = Image.fromarray(a.copy()); dr = ImageDraw.Draw(img)
        dr.rectangle([0, 0, img.width, 52], fill=(0, 0, 0)); dr.text((16, 8), title, font=font, fill=(255, 255, 255))
        img.save(P + "/vista_%s.png" % name)
        print("SHOT", name, flush=True)

    mid = (c_t + entry) / 2
    shot("1_oblicua", mid, (-0.6, 0.7, 0.5), 330, "Plantilla (verde azulado), contorno de craneotomía (rojo) y tumor (amarillo)")
    shot("2_superior", mid, (0, 0.05, 1), 330, "Vista superior", up=(0, 1, 0))
    tpl.GetDisplayNode().SetVisibility(False)
    shot("3_sin_plantilla", mid, (-0.6, 0.7, 0.5), 330, "Sin plantilla: contorno marcado sobre la piel y trayectoria")
    tpl.GetDisplayNode().SetVisibility(True)
    vn.SetRenderMode(slicer.vtkMRMLViewNode.Orthographic); pump(5); cam.SetParallelScale(75)
    shot("4_eje", entry, tuple(d), 260, "Vista ortográfica a lo largo de la trayectoria: margen de 10 mm alrededor del tumor", up=(0, 1, 0))
    skin.GetDisplayNode().SetVisibility(False)
    shot("5_eje_sin_piel", entry, tuple(d), 260, "Plantilla sola (sin piel), vista ortográfica", up=(0, 1, 0))
    vn.SetRenderMode(slicer.vtkMRMLViewNode.Perspective)
    shot("6_oblicua_sin_piel", mid, (0.6, -0.2, 0.8), 300, "Plantilla sola, vista oblicua desde el otro lado")
    print("T4_DONE", flush=True)
except Exception:
    print("ERR", traceback.format_exc(), flush=True)
slicer.app.quit()
