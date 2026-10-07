import json, math, time
import numpy as np, vtk
from vtk.util.numpy_support import vtk_to_numpy, numpy_to_vtk
from scipy import ndimage as ndi

P = "C:/Users/Laboratorio/Downloads/pelvis_guia"
COS45 = math.cos(math.radians(45))
t0 = time.time()
g = np.load(P + "/guia_geom.npz")
c_a, axis = g["c_a"], g["axis"]


def read_pd(fn):
    r = vtk.vtkSTLReader(); r.SetFileName(fn); r.Update()
    c = vtk.vtkCleanPolyData(); c.SetInputData(r.GetOutput()); c.Update()
    t = vtk.vtkTriangleFilter(); t.SetInputData(c.GetOutput()); t.Update()
    return t.GetOutput()


def arrays(pd):
    X = vtk_to_numpy(pd.GetPoints().GetData()).astype(np.float64)
    T = vtk_to_numpy(pd.GetPolys().GetData()).reshape(-1, 4)[:, 1:]
    a, b, c = X[T[:, 0]], X[T[:, 1]], X[T[:, 2]]
    nrm = np.cross(b - a, c - a)
    area = 0.5 * np.linalg.norm(nrm, axis=1)
    nrm = nrm / np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
    cen = (a + b + c) / 3
    return X, T, nrm, area, cen


def fib(n):
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    th = math.pi * (1 + 5 ** 0.5) * i
    return np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)], axis=1)


def overhang(nrm, area, cen, up):
    h = cen @ up
    base = h < h.min() + 0.3
    down = (nrm @ (-up)) > COS45
    return float(area[down & ~base].sum()), float(h.max() - h.min()), float(area[base].sum())


def best_orientation(pd, prefer_axis=None):
    X, T, nrm, area, cen = arrays(pd)
    res = []
    for u in fib(700):
        ov, hgt, bs = overhang(nrm, area, cen, u)
        res.append((ov, hgt, bs, u))
    res.sort(key=lambda r: (r[0], r[1]))
    best = res[0]
    out = dict(total_area=float(area.sum()))
    cand = []
    if prefer_axis is not None:
        for s in (1, -1):
            u = s * prefer_axis
            ov, hgt, bs = overhang(nrm, area, cen, u)
            cand.append((ov, hgt, bs, u))
        cand.sort(key=lambda r: r[0])
    return best, (cand[0] if cand else None), out


def orient(pd, up, center_xy=(0.0, 0.0)):
    up = up / np.linalg.norm(up)
    ref = np.array([1, 0, 0.0]) if abs(up[0]) < 0.9 else np.array([0, 1, 0.0])
    x = np.cross(ref, up); x /= np.linalg.norm(x)
    y = np.cross(up, x)
    R = np.stack([x, y, up])                       # filas: nuevo x,y,z
    m = vtk.vtkMatrix4x4()
    for i in range(3):
        for j in range(3):
            m.SetElement(i, j, R[i, j])
    tr = vtk.vtkTransform(); tr.SetMatrix(m)
    tf = vtk.vtkTransformPolyDataFilter(); tf.SetInputData(pd); tf.SetTransform(tr); tf.Update()
    o = tf.GetOutput()
    b = o.GetBounds()
    t2 = vtk.vtkTransform()
    t2.Translate(center_xy[0] - (b[0] + b[1]) / 2, center_xy[1] - (b[2] + b[3]) / 2, -b[4])
    tf2 = vtk.vtkTransformPolyDataFilter(); tf2.SetInputData(o); tf2.SetTransform(t2); tf2.Update()
    return tf2.GetOutput()


def stats(pd):
    fe = vtk.vtkFeatureEdges(); fe.SetInputData(pd); fe.BoundaryEdgesOn(); fe.NonManifoldEdgesOn(); fe.FeatureEdgesOff(); fe.ManifoldEdgesOff(); fe.Update()
    mp = vtk.vtkMassProperties(); mp.SetInputData(pd); mp.Update()
    b = pd.GetBounds()
    return dict(tri=int(pd.GetNumberOfCells()), bordes_abiertos=int(fe.GetOutput().GetNumberOfCells()),
                volumen_mm3=round(abs(mp.GetVolume())), dims_mm=[round(b[1] - b[0], 1), round(b[3] - b[2], 1), round(b[5] - b[4], 1)])


def write(pd, fn):
    w = vtk.vtkSTLWriter(); w.SetFileName(fn); w.SetInputData(pd); w.SetFileTypeToBinary(); w.Write()


def thickness(pd, res=0.5):
    b = pd.GetBounds()
    org = np.array([b[0], b[2], b[4]]) - 3
    dims = [int((b[2 * i + 1] - b[2 * i] + 6) / res) + 1 for i in range(3)]
    img = vtk.vtkImageData(); img.SetDimensions(*dims); img.SetSpacing(res, res, res); img.SetOrigin(*org)
    img.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1); img.GetPointData().GetScalars().Fill(255)
    st = vtk.vtkPolyDataToImageStencil(); st.SetInputData(pd); st.SetOutputOrigin(*org); st.SetOutputSpacing(res, res, res); st.SetOutputWholeExtent(img.GetExtent()); st.Update()
    ims = vtk.vtkImageStencil(); ims.SetInputData(img); ims.SetStencilConnection(st.GetOutputPort()); ims.SetBackgroundValue(0); ims.Update()
    m = vtk_to_numpy(ims.GetOutput().GetPointData().GetScalars()).reshape(dims[2], dims[1], dims[0]) > 0
    edt = ndi.distance_transform_edt(m, sampling=res)
    ridge = (ndi.maximum_filter(edt, size=3) == edt) & (edt > 0.6)
    th = 2 * edt[ridge]
    return dict(espesor_local_p5_mm=round(float(np.percentile(th, 5)), 2), espesor_local_mediana_mm=round(float(np.median(th)), 2),
                espesor_local_min_mm=round(float(th.min()), 2))


def with_overhang(pd):
    X, T, nrm, area, cen = arrays(pd)
    flag = ((nrm @ np.array([0, 0, -1.0])) > COS45) & (cen[:, 2] > cen[:, 2].min() + 0.3)
    out = vtk.vtkPolyData(); out.DeepCopy(pd)
    a = numpy_to_vtk(flag.astype(np.float32), deep=True); a.SetName("voladizo")
    out.GetCellData().AddArray(a); out.GetCellData().SetActiveScalars("voladizo")
    return out, float(area[flag].sum() / area.sum())


report = {}
# ---------------- guia ----------------
guide = read_pd(P + "/guia_copa_acetabular.stl")
best, axisc, info = best_orientation(guide, prefer_axis=axis)
ov_free, h_free, bs_free, u_free = best
ov_ax, h_ax, bs_ax, u_ax = axisc
tot = info["total_area"]
# eje del tubo vertical si no empeora mucho el voladizo (agujero mas redondo)
if ov_ax <= 1.35 * ov_free + 1.0:
    up, why = u_ax, "eje del tubo vertical (orificio más circular)"
else:
    up, why = u_free, "orientación de mínimo voladizo"
g_or = orient(guide, up, (-55.0, 0.0))
report["guia"] = dict(orientacion=why, voladizo_libre_pct=round(100 * ov_free / tot, 1), voladizo_eje_vertical_pct=round(100 * ov_ax / tot, 1),
                      altura_impresion_mm=round(g_or.GetBounds()[5], 1), **stats(g_or), **thickness(g_or))
write(g_or, P + "/imprimir_guia.stl")
g_vis, frac = with_overhang(g_or)
report["guia"]["voladizo_elegido_pct"] = round(100 * frac, 1)
w = vtk.vtkXMLPolyDataWriter(); w.SetFileName(P + "/imprimir_guia_voladizos.vtp"); w.SetInputData(g_vis); w.Write()
print("GUIA", report["guia"], flush=True)

# ---------------- replica osea del acetabulo ----------------
hip = read_pd(P + "/modelos/Hip_R.stl")
RES = 0.8
R_CUT = 70.0
org = c_a - R_CUT - 3
n = int((2 * R_CUT + 6) / RES) + 1
img = vtk.vtkImageData(); img.SetDimensions(n, n, n); img.SetSpacing(RES, RES, RES); img.SetOrigin(*org)
img.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1); img.GetPointData().GetScalars().Fill(255)
st = vtk.vtkPolyDataToImageStencil(); st.SetInputData(hip); st.SetOutputOrigin(*org); st.SetOutputSpacing(RES, RES, RES); st.SetOutputWholeExtent(img.GetExtent()); st.Update()
ims = vtk.vtkImageStencil(); ims.SetInputData(img); ims.SetStencilConnection(st.GetOutputPort()); ims.SetBackgroundValue(0); ims.Update()
bone = vtk_to_numpy(ims.GetOutput().GetPointData().GetScalars()).reshape(n, n, n) > 0
zz, yy, xx = np.meshgrid(org[2] + RES * np.arange(n), org[1] + RES * np.arange(n), org[0] + RES * np.arange(n), indexing="ij")
sph = ((xx - c_a[0]) ** 2 + (yy - c_a[1]) ** 2 + (zz - c_a[2]) ** 2) <= R_CUT ** 2
blk = bone & sph
lab, nl = ndi.label(blk)
sz = ndi.sum(blk, lab, range(1, nl + 1))
blk = lab == (int(np.argmax(sz)) + 1)
im2 = vtk.vtkImageData(); im2.SetDimensions(n, n, n); im2.SetSpacing(RES, RES, RES); im2.SetOrigin(*org)
im2.GetPointData().SetScalars(numpy_to_vtk(ndi.gaussian_filter(blk.astype(np.float32), 0.7).ravel(), deep=True, array_type=vtk.VTK_FLOAT))
fe = vtk.vtkFlyingEdges3D(); fe.SetInputData(im2); fe.SetValue(0, 0.5); fe.ComputeNormalsOff(); fe.Update()
sm = vtk.vtkWindowedSincPolyDataFilter(); sm.SetInputData(fe.GetOutput()); sm.SetNumberOfIterations(15); sm.BoundarySmoothingOff(); sm.NonManifoldSmoothingOn(); sm.NormalizeCoordinatesOn(); sm.Update()
cl = vtk.vtkCleanPolyData(); cl.SetInputData(sm.GetOutput()); cl.Update()
rep = cl.GetOutput()
write(rep, P + "/replica_hueso_acetabulo_sin_orientar.stl")
bestR, _, infoR = best_orientation(rep)
ovR, hR, bsR, uR = bestR
r_or = orient(rep, uR, (55.0, 0.0))
# base plana: recorte a 3 mm sobre el plano de cama
pl = vtk.vtkPlaneCollection(); p1 = vtk.vtkPlane(); p1.SetOrigin(0, 0, 3.0); p1.SetNormal(0, 0, 1); pl.AddItem(p1)
cc = vtk.vtkClipClosedSurface(); cc.SetInputData(r_or); cc.SetClippingPlanes(pl); cc.Update()
tfm = vtk.vtkTransform(); tfm.Translate(0, 0, -3.0)
tfp = vtk.vtkTransformPolyDataFilter(); tfp.SetInputData(cc.GetOutput()); tfp.SetTransform(tfm); tfp.Update()
cl2 = vtk.vtkCleanPolyData(); cl2.SetInputData(tfp.GetOutput()); cl2.Update()
tri2 = vtk.vtkTriangleFilter(); tri2.SetInputData(cl2.GetOutput()); tri2.Update()
r_fin = tri2.GetOutput()
report["replica"] = dict(descripcion="Coxal derecho recortado a una esfera de 70 mm alrededor del acetábulo, con base plana", voladizo_pct=round(100 * ovR / infoR["total_area"], 1),
                         **stats(r_fin))
write(r_fin, P + "/imprimir_replica_hueso.stl")
r_vis, fr = with_overhang(r_fin)
report["replica"]["voladizo_elegido_pct"] = round(100 * fr, 1)
w = vtk.vtkXMLPolyDataWriter(); w.SetFileName(P + "/imprimir_replica_voladizos.vtp"); w.SetInputData(r_vis); w.Write()
print("REPLICA", report["replica"], flush=True)

# masa orientativa (PLA 1.24 g/cm3, 100 % y 20 % de relleno ~ 40 % del volumen con paredes)
for k in ("guia", "replica"):
    v = report[k]["volumen_mm3"] / 1000.0
    report[k]["masa_pla_100pct_g"] = round(v * 1.24, 1)
    report[k]["masa_pla_relleno20_aprox_g"] = round(v * 1.24 * 0.45, 1)
report["parametros_recomendados_prueba"] = dict(
    escala="100 % (mm)", material="PLA o PETG (solo banco de pruebas; no apto para uso clínico)", altura_capa_mm=0.15,
    paredes=3, relleno_pct=20, soportes="solo en zonas en rojo (voladizo > 45°)", boquilla_mm=0.4,
    nota="Los valores de masa y tiempo son estimaciones; el laminador dará los reales.")
report["tiempo_s"] = round(time.time() - t0, 1)
json.dump(report, open(P + "/impresion_plan.json", "w"), indent=1, ensure_ascii=False)
print("G3_DONE", flush=True)
