import json, math, time, zipfile
import numpy as np, vtk
from vtk.util.numpy_support import vtk_to_numpy, numpy_to_vtk
from scipy import ndimage as ndi

P = "C:/Users/Laboratorio/Downloads/tumor_cerebral"
COS45 = math.cos(math.radians(45))
g = np.load(P + "/plan_geom.npz")
d_traj = g["d"]


def read_pd(fn):
    r = vtk.vtkSTLReader(); r.SetFileName(fn); r.Update()
    c = vtk.vtkCleanPolyData(); c.SetInputData(r.GetOutput()); c.Update()
    t = vtk.vtkTriangleFilter(); t.SetInputData(c.GetOutput()); t.Update()
    return t.GetOutput()


def arrays(pd):
    X = vtk_to_numpy(pd.GetPoints().GetData()).astype(np.float64)
    T = vtk_to_numpy(pd.GetPolys().GetData()).reshape(-1, 4)[:, 1:]
    a, b, c = X[T[:, 0]], X[T[:, 1]], X[T[:, 2]]
    n = np.cross(b - a, c - a); area = 0.5 * np.linalg.norm(n, axis=1)
    n = n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    return X, T, n, area, (a + b + c) / 3


def overhang(n, area, cen, up):
    h = cen @ up
    base = h < h.min() + 0.3
    return float(area[((n @ (-up)) > COS45) & ~base].sum()), float(h.max() - h.min())


def best_up(pd):
    X, T, n, area, cen = arrays(pd)
    i = np.arange(700) + 0.5
    phi = np.arccos(1 - 2 * i / 700); th = math.pi * (1 + 5 ** 0.5) * i
    U = np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)], 1)
    res = sorted([(overhang(n, area, cen, u)[0], overhang(n, area, cen, u)[1], tuple(u)) for u in U])
    return np.array(res[0][2]), res[0][0] / area.sum()


def orient(pd, up, cxy):
    up = up / np.linalg.norm(up)
    ref = np.array([1, 0, 0.0]) if abs(up[0]) < 0.9 else np.array([0, 1, 0.0])
    x = np.cross(ref, up); x /= np.linalg.norm(x); y = np.cross(up, x)
    m = vtk.vtkMatrix4x4()
    for r_, row in enumerate((x, y, up)):
        for c_ in range(3):
            m.SetElement(r_, c_, row[c_])
    tr = vtk.vtkTransform(); tr.SetMatrix(m)
    tf = vtk.vtkTransformPolyDataFilter(); tf.SetInputData(pd); tf.SetTransform(tr); tf.Update()
    o = tf.GetOutput(); b = o.GetBounds()
    t2 = vtk.vtkTransform(); t2.Translate(cxy[0] - (b[0] + b[1]) / 2, cxy[1] - (b[2] + b[3]) / 2, -b[4])
    tf2 = vtk.vtkTransformPolyDataFilter(); tf2.SetInputData(o); tf2.SetTransform(t2); tf2.Update()
    return tf2.GetOutput()


def stats(pd):
    fe = vtk.vtkFeatureEdges(); fe.SetInputData(pd); fe.BoundaryEdgesOn(); fe.NonManifoldEdgesOn(); fe.FeatureEdgesOff(); fe.ManifoldEdgesOff(); fe.Update()
    mp = vtk.vtkMassProperties(); mp.SetInputData(pd); mp.Update(); b = pd.GetBounds()
    return dict(tri=int(pd.GetNumberOfCells()), bordes_abiertos=int(fe.GetOutput().GetNumberOfCells()), volumen_mm3=round(abs(mp.GetVolume())),
                dims_mm=[round(b[1] - b[0], 1), round(b[3] - b[2], 1), round(b[5] - b[4], 1)])


def thickness(pd, res=0.4):
    b = pd.GetBounds(); org = np.array([b[0], b[2], b[4]]) - 3
    dims = [int((b[2 * i + 1] - b[2 * i] + 6) / res) + 1 for i in range(3)]
    img = vtk.vtkImageData(); img.SetDimensions(*dims); img.SetSpacing(res, res, res); img.SetOrigin(*org)
    img.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1); img.GetPointData().GetScalars().Fill(255)
    st = vtk.vtkPolyDataToImageStencil(); st.SetInputData(pd); st.SetOutputOrigin(*org); st.SetOutputSpacing(res, res, res); st.SetOutputWholeExtent(img.GetExtent()); st.Update()
    ims = vtk.vtkImageStencil(); ims.SetInputData(img); ims.SetStencilConnection(st.GetOutputPort()); ims.SetBackgroundValue(0); ims.Update()
    m = vtk_to_numpy(ims.GetOutput().GetPointData().GetScalars()).reshape(dims[2], dims[1], dims[0]) > 0
    edt = ndi.distance_transform_edt(m, sampling=res)
    ridge = (ndi.maximum_filter(edt, size=3) == edt) & (edt > 0.5)
    th = 2 * edt[ridge]
    return dict(espesor_p5_mm=round(float(np.percentile(th, 5)), 2), espesor_mediana_mm=round(float(np.median(th)), 2), espesor_min_mm=round(float(th.min()), 2))


def with_overhang(pd, fn):
    X, T, n, area, cen = arrays(pd)
    flag = ((n @ np.array([0, 0, -1.0])) > COS45) & (cen[:, 2] > cen[:, 2].min() + 0.3)
    o = vtk.vtkPolyData(); o.DeepCopy(pd)
    a = numpy_to_vtk(flag.astype(np.float32), deep=True); a.SetName("voladizo"); o.GetCellData().AddArray(a)
    w = vtk.vtkXMLPolyDataWriter(); w.SetFileName(fn); w.SetInputData(o); w.Write()
    return round(100 * float(area[flag].sum() / area.sum()), 1)


def write(pd, fn):
    w = vtk.vtkSTLWriter(); w.SetFileName(fn); w.SetInputData(pd); w.SetFileTypeToBinary(); w.Write()


rep = {}
# plantilla
tpl = read_pd(P + "/plantilla_craneotomia.stl")
u, ov = best_up(tpl)
tpl_o = orient(tpl, u, (55.0, -20.0))
write(tpl_o, P + "/imprimir_plantilla.stl")
rep["plantilla"] = dict(voladizo_pct=with_overhang(tpl_o, P + "/imprimir_plantilla_voladizos.vtp"), altura_mm=round(tpl_o.GetBounds()[5], 1), **stats(tpl_o), **thickness(tpl_o))
# maniqui: base plana perpendicular a la trayectoria -> arriba = direccion de la trayectoria
man = read_pd(P + "/maniqui_prueba_cuero_cabelludo.stl")
man_o = orient(man, d_traj, (-55.0, -20.0))
write(man_o, P + "/imprimir_maniqui.stl")
rep["maniqui"] = dict(voladizo_pct=with_overhang(man_o, P + "/imprimir_maniqui_voladizos.vtp"), altura_mm=round(man_o.GetBounds()[5], 1), **stats(man_o))
# modelo del tumor (1:1)
tum = read_pd(P + "/tumor_modelo.stl")
u, ov = best_up(tum)
tum_o = orient(tum, u, (0.0, 75.0))
write(tum_o, P + "/imprimir_tumor.stl")
rep["tumor"] = dict(voladizo_pct=with_overhang(tum_o, P + "/imprimir_tumor_voladizos.vtp"), altura_mm=round(tum_o.GetBounds()[5], 1), **stats(tum_o))
for k, v in rep.items():
    print("PIEZA", k, v, flush=True)


# 3MF con las tres piezas en la cama de 220 x 220 (centro 110,110)
def obj_xml(oid, name, pd):
    X = vtk_to_numpy(pd.GetPoints().GetData()); T = vtk_to_numpy(pd.GetPolys().GetData()).reshape(-1, 4)[:, 1:]
    v = "".join('<vertex x="%.4f" y="%.4f" z="%.4f"/>' % tuple(p) for p in X)
    t = "".join('<triangle v1="%d" v2="%d" v3="%d"/>' % tuple(f) for f in T)
    return '<object id="%d" name="%s" type="model"><mesh><vertices>%s</vertices><triangles>%s</triangles></mesh></object>' % (oid, name, v, t)


items = [("plantilla_craneotomia", tpl_o), ("maniqui_prueba", man_o), ("tumor_modelo", tum_o)]
model = ('<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources>'
         + "".join(obj_xml(i + 1, n, p) for i, (n, p) in enumerate(items)) + '</resources><build>'
         + "".join('<item objectid="%d" transform="1 0 0 0 1 0 0 0 1 110 110 0"/>' % (i + 1) for i in range(len(items))) + '</build></model>')
ct = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
      '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
      '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
with zipfile.ZipFile(P + "/placa_craneotomia.3mf", "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("[Content_Types].xml", ct); z.writestr("_rels/.rels", rels); z.writestr("3D/3dmodel.model", model)
allb = np.array([p.GetBounds() for _, p in items])
print("PLACA x", allb[:, 0].min().round(1), allb[:, 1].max().round(1), "y", allb[:, 2].min().round(1), allb[:, 3].max().round(1), flush=True)
json.dump(rep, open(P + "/impresion_plan.json", "w"), indent=1, ensure_ascii=False)
print("T5_DONE", flush=True)
