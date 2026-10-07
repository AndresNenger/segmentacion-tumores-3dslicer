import slicer, vtk, numpy as np, traceback
from vtk.util.numpy_support import vtk_to_numpy
from PIL import Image, ImageDraw, ImageFont

P = "C:/Users/Laboratorio/Downloads/pelvis_guia"
mw = slicer.util.mainWindow()
mw.showMaximized()


def pump(n=5):
    for _ in range(n):
        slicer.app.processEvents()


try:
    t0 = __import__("time").time()
    while __import__("time").time() - t0 < 3:
        pump()
    lm = slicer.app.layoutManager()
    lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUp3DView)
    pump()
    view = lm.threeDWidget(0).threeDView()
    vn = view.mrmlViewNode()
    vn.SetBoxVisible(False)
    vn.SetAxisLabelsVisible(False)
    vn.SetBackgroundColor(0.05, 0.06, 0.10)
    vn.SetBackgroundColor2(0.22, 0.28, 0.36)
    g = np.load(P + "/guia_geom.npz")
    c_a, axis = g["c_a"], g["axis"]

    def load(fn, col, op=1.0):
        m = slicer.util.loadNodeFromFile(P + "/" + fn, "ModelFile", {"coordinateSystem": "RAS"})
        d = m.GetDisplayNode()
        d.SetColor(*col)
        d.SetOpacity(op)
        d.SetAmbient(0.25)
        d.SetDiffuse(0.8)
        d.SetSpecular(0.25)
        return m

    load("modelos/Hip_R.stl", (0.90, 0.88, 0.82), 1.0)
    load("modelos/Hip_L.stl", (0.80, 0.80, 0.78), 0.35)
    load("modelos/Sacrum.stl", (0.80, 0.80, 0.78), 0.35)
    load("guia_copa_acetabular.stl", (0.10, 0.75, 0.70), 1.0)
    load("copa_referencia_48mm.stl", (0.25, 0.45, 0.95), 0.45)
    load("eje_planificado.stl", (1.0, 0.2, 0.15), 1.0)
    pump(10)
    rw = view.renderWindow()
    ren = rw.GetRenderers().GetFirstRenderer()
    cam = slicer.modules.cameras.logic().GetViewActiveCameraNode(vn).GetCamera()
    focal = c_a + axis * 22.0
    font = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 30)

    def shot(name, direction, dist, up=(0, 0, 1), title=""):
        d = np.array(direction, float)
        d /= np.linalg.norm(d)
        cam.SetFocalPoint(*focal)
        cam.SetPosition(*(focal + d * dist))
        cam.SetViewUp(*up)
        ren.ResetCameraClippingRange()
        pump(8)
        view.forceRender()
        w2i = vtk.vtkWindowToImageFilter()
        w2i.SetInput(rw)
        w2i.SetInputBufferTypeToRGB()
        w2i.ReadFrontBufferOff()
        w2i.Update()
        im = w2i.GetOutput()
        dims = im.GetDimensions()
        a = vtk_to_numpy(im.GetPointData().GetScalars()).reshape(dims[1], dims[0], 3)[::-1]
        img = Image.fromarray(a.copy())
        dr = ImageDraw.Draw(img)
        dr.rectangle([0, 0, img.width, 52], fill=(0, 0, 0))
        dr.text((16, 8), title, font=font, fill=(255, 255, 255))
        img.save(P + "/vista_%s.png" % name)
        print("SHOT", name, img.size, flush=True)

    shot("1_lateral", (1, 0, 0), 260, title="Vista lateral: guía (verde azulado) sobre el coxal derecho")
    shot("2_anterior", (0.0, 1, 0.0), 260, title="Vista anterior")
    shot("3_oblicua", (0.7, 0.7, 0.35), 240, title="Vista oblicua con copa de 48 mm (azul) y eje planificado (rojo)")
    shot("4_eje_visual", tuple(axis), 260, up=(0, 0, 1), title="Vista a lo largo del eje de la copa (orificio guía concéntrico)")
    print("G2_DONE", flush=True)
except Exception:
    print("ERR", traceback.format_exc(), flush=True)
slicer.app.quit()
