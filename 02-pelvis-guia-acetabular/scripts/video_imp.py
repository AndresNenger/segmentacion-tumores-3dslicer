import sys, time, subprocess, json
sys.path.append("C:/Users/Laboratorio/Downloads/femur_vh/deps_vid")
import slicer, vtk, qt, numpy as np
import imageio_ffmpeg

P = "C:/Users/Laboratorio/Downloads/pelvis_guia"
OUT = P + "/segmento_impresion.mp4"
FPS = 24
DT = 1.0 / FPS
plan = json.load(open(P + "/impresion_plan.json"))

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


def addpoly(name, pd, col, op=1.0):
    n = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode", name)
    n.SetAndObservePolyData(pd)
    n.CreateDefaultDisplayNodes()
    d = n.GetDisplayNode()
    d.SetColor(*col)
    d.SetOpacity(op)
    d.SetVisibility(False)
    return n


def read_vtp(fn):
    r = vtk.vtkXMLPolyDataReader()
    r.SetFileName(fn)
    r.Update()
    o = vtk.vtkPolyData()
    o.DeepCopy(r.GetOutput())
    return o


# paleta: 0 = gris (sin soporte), 1 = rojo (voladizo)
ct = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLColorTableNode", "voladizo")
ct.SetTypeToUser()
ct.SetNumberOfColors(256)
for i in range(256):
    if i < 128:
        ct.SetColor(i, "g%d" % i, 0.86, 0.86, 0.80, 1.0)
    else:
        ct.SetColor(i, "r%d" % i, 1.0, 0.15, 0.10, 1.0)


def part(name, fn):
    n = addpoly(name, read_vtp(fn), (1, 1, 1))
    d = n.GetDisplayNode()
    d.SetActiveScalarName("voladizo")
    d.SetActiveAttributeLocation(vtk.vtkAssignAttribute.CELL_DATA)
    d.SetAndObserveColorNodeID(ct.GetID())
    d.SetScalarRangeFlag(slicer.vtkMRMLDisplayNode.UseManualScalarRange)
    d.SetScalarRange(0, 1)
    d.SetScalarVisibility(True)
    d.SetAmbient(0.25)
    d.SetDiffuse(0.8)
    d.SetSpecular(0.2)
    return n


guide = part("guia_impresion", P + "/imprimir_guia_voladizos.vtp")
repl = part("replica_impresion", P + "/imprimir_replica_voladizos.vtp")

cube = vtk.vtkCubeSource()
cube.SetBounds(-110, 110, -110, 110, -3, 0)
cube.Update()
bp = vtk.vtkPolyData()
bp.DeepCopy(cube.GetOutput())
bed = addpoly("cama_220x220", bp, (0.38, 0.42, 0.48), 1.0)

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


set_view((0, 0, 45), (0, -1, 0.55), 360)
bed.GetDisplayNode().SetVisibility(True)
cap("Paso 8: preparar los STL para el modelo físico", "Placa de impresión de 220 × 220 mm (Creality K1C) · escala 1:1 (mm)")
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
    ang = np.radians(deg / n)
    ca, sa = np.cos(ang), np.sin(ang)
    for _ in range(n):
        f = np.array(cam.GetFocalPoint())
        p = np.array(cam.GetPosition()) - f
        p = np.array([ca * p[0] - sa * p[1], sa * p[0] + ca * p[1], p[2]])
        cam.SetPosition(*(f + p))
        cam.SetViewUp(0, 0, 1)
        tick()


def fade_in(node, sec):
    dn = node.GetDisplayNode()
    dn.SetOpacity(0.0)
    dn.SetVisibility(True)
    n = max(int(sec * FPS), 1)
    for i in range(1, n + 1):
        dn.SetOpacity(i / n)
        tick()


gi, ri = plan["guia"], plan["replica"]
try:
    hold(2.0)
    cap("Guía en orientación de impresión: tubo en vertical",
        "Rojo = voladizo > 45° (%.1f %% de la superficie, necesita soportes) · malla cerrada (0 aristas abiertas) · altura %.0f mm"
        % (gi["voladizo_elegido_pct"], gi["altura_impresion_mm"]))
    fade_in(guide, 1.2)
    orbit(6.0, 150)
    cap("Réplica ósea del acetábulo con base plana",
        "Coxal derecho recortado a 70 mm alrededor del acetábulo · %.0f cm³ · sirve para probar el asiento de la guía" % (ri["volumen_mm3"] / 1000.0))
    fade_in(repl, 1.2)
    orbit(6.5, 150)
    cap("Punto a vigilar: espesor local mínimo de %.1f mm" % gi["espesor_local_min_mm"],
        "Mediana %.1f mm · percentil 5: %.1f mm (bordes de los parches) · engrosar antes de un uso real; los puntales de Ø 5,2 mm pueden flexar"
        % (gi["espesor_local_mediana_mm"], gi["espesor_local_p5_mm"]))
    orbit(5.5, 100)
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
