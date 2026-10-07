import sys, json, math, time
import numpy as np, vtk
from vtk.util.numpy_support import vtk_to_numpy, numpy_to_vtk
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

P = "C:/Users/Laboratorio/Downloads/pelvis_guia"
INCL, ANTV = 40.0, 15.0          # inclinacion / anteversion radiografica objetivo (zona de Lewinnek), grados
RES = 0.7                        # mm por voxel
T_SHELL = 3.0                    # espesor del parche de contacto (mm)
CLEAR = 0.3                      # holgura guia-hueso (mm)
TUBE_RO, TUBE_RI, TUBE_L = 8.0, 4.6, 30.0
STRUT_R, PIN_R = 2.6, 1.3
t_start = time.time()


def read_stl(fn):
    r = vtk.vtkSTLReader(); r.SetFileName(fn); r.Update()
    c = vtk.vtkCleanPolyData(); c.SetInputData(r.GetOutput()); c.Update()
    p = c.GetOutput()
    return p, vtk_to_numpy(p.GetPoints().GetData()).astype(np.float64)


def unit(v):
    return v / np.linalg.norm(v)


hipR_pd, XR = read_stl(P + "/modelos/Hip_R.stl")
hipL_pd, XL = read_stl(P + "/modelos/Hip_L.stl")
_, XS = read_stl(P + "/modelos/Sacrum.stl")
bc = np.load(P + "/fea_bc_h4.5.npz")
head_c = bc["head"].astype(float)
head_R = float(bc["R"])

# ---------- 1. acetabulo: esfera ajustada a la superficie del coxal derecho ----------
pts = XR[np.linalg.norm(XR - head_c, axis=1) < 36.0]
rng = np.random.default_rng(1)
best = (0, None)
for _ in range(6000):
    q = pts[rng.choice(len(pts), 4, replace=False)]
    A = np.c_[2 * q, np.ones(4)]
    b = (q ** 2).sum(1)
    try:
        sol = np.linalg.solve(A, b)
    except np.linalg.LinAlgError:
        continue
    c = sol[:3]
    R = math.sqrt(max(sol[3] + c @ c, 0))
    if not (19 < R < 30) or np.linalg.norm(c - head_c) > 8:
        continue
    n = (np.abs(np.linalg.norm(pts - c, axis=1) - R) < 1.0).sum()
    if n > best[0]:
        best = (n, (c, R))
c_a, R_a = best[1]
for _ in range(6):
    inl = pts[np.abs(np.linalg.norm(pts - c_a, axis=1) - R_a) < 1.5]
    A = np.c_[2 * inl, np.ones(len(inl))]
    b = (inl ** 2).sum(1)
    sol = np.linalg.lstsq(A, b, rcond=None)[0]
    c_a = sol[:3]
    R_a = float(math.sqrt(sol[3] + c_a @ c_a))
cup_D = int(2 * round(R_a))                 # diametro de copa (mm), par
print("ACETABULO centro", c_a.round(1).tolist(), "radio", round(R_a, 1), "inliers", best[0], "copa", cup_D, flush=True)

# ---------- 2. sistema de coordenadas pelvico (plano pelvico anterior) ----------
def asis(X):
    top = X[:, 2].max()
    cand = X[X[:, 2] > top - 90]
    return cand[np.argmax(cand[:, 1])]


asis_R, asis_L = asis(XR), asis(XL)
tL = cKDTree(XL)
dd, _ = tL.query(XR)
sym = XR[dd < 8.0]
S = sym[np.argmax(sym[:, 1])]                # punto anterior de la sinfisis (aprox. tuberculo pubico)
n_app = np.cross(asis_R - S, asis_L - S)
n_app = unit(n_app)
if n_app[1] < 0:
    n_app = -n_app
x_p = unit(asis_R - asis_L)
z_p = unit(np.cross(x_p, n_app))
if z_p[2] < 0:
    z_p = -z_p
y_p = unit(np.cross(z_p, x_p))
print("PELVIS ASIS_R", asis_R.round(1).tolist(), "ASIS_L", asis_L.round(1).tolist(), "sinfisis", S.round(1).tolist(), flush=True)
print("PELVIS ejes x", x_p.round(3).tolist(), "y", y_p.round(3).tolist(), "z", z_p.round(3).tolist(), flush=True)

# ---------- 3. eje objetivo de la copa (coxal derecho: lateral = +x) ----------
ai, aa = math.radians(INCL), math.radians(ANTV)
ay = math.sin(aa)
rest = math.sqrt(1 - ay ** 2)
a_p = np.array([rest * math.sin(ai), ay, -rest * math.cos(ai)])
axis = unit(a_p[0] * x_p + a_p[1] * y_p + a_p[2] * z_p)
# comprobacion de los angulos a partir del eje final
ap_chk = np.array([axis @ x_p, axis @ y_p, axis @ z_p])
incl_chk = math.degrees(math.atan2(ap_chk[0], -ap_chk[2]))
antv_chk = math.degrees(math.asin(ap_chk[1]))
print("EJE", axis.round(3).tolist(), "incl", round(incl_chk, 1), "antev", round(antv_chk, 1), flush=True)

# ---------- 4. rejilla voxel ----------
center = c_a + axis * 22.0
half = 78.0
n = int(2 * half / RES) + 1
org = center - half
shape = (n, n, n)                              # (z, y, x)
xs = (org[0] + RES * np.arange(n)).astype(np.float32)
ys = (org[1] + RES * np.arange(n)).astype(np.float32)
zs = (org[2] + RES * np.arange(n)).astype(np.float32)
Z, Y, Xg = np.meshgrid(zs, ys, xs, indexing="ij")


def to_vtk_image(arr, dtype=vtk.VTK_FLOAT):
    img = vtk.vtkImageData()
    img.SetDimensions(n, n, n)
    img.SetSpacing(RES, RES, RES)
    img.SetOrigin(*org)
    img.GetPointData().SetScalars(numpy_to_vtk(arr.ravel(order="C"), deep=True, array_type=dtype))
    return img


# hueso voxelizado
img = vtk.vtkImageData()
img.SetDimensions(n, n, n); img.SetSpacing(RES, RES, RES); img.SetOrigin(*org)
img.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1); img.GetPointData().GetScalars().Fill(255)
st = vtk.vtkPolyDataToImageStencil()
st.SetInputData(hipR_pd); st.SetOutputOrigin(*org); st.SetOutputSpacing(RES, RES, RES); st.SetOutputWholeExtent(img.GetExtent()); st.Update()
ims = vtk.vtkImageStencil(); ims.SetInputData(img); ims.SetStencilConnection(st.GetOutputPort()); ims.SetBackgroundValue(0); ims.Update()
bone = vtk_to_numpy(ims.GetOutput().GetPointData().GetScalars()).reshape(shape) > 0
print("HUESO voxeles", int(bone.sum()), flush=True)
dist = ndi.distance_transform_edt(~bone, sampling=RES).astype(np.float32)   # distancia al hueso (fuera)

# sanity: el eje sale del acetabulo (vacio lateral) y la pared medial es hueso
def vox(p):
    i = np.round((p - org) / RES).astype(int)
    return bone[i[2], i[1], i[0]]


lat_ok = not vox(c_a + axis * (R_a * 0.4))
med_ok = vox(c_a - axis * (R_a + 2.0)) or vox(c_a - axis * (R_a + 5.0))
print("COMPROBACION eje: lateral vacio", lat_ok, "| pared medial hueso", bool(med_ok), flush=True)

# ---------- 5. parches de contacto ----------
rel = np.stack([Xg - c_a[0], Y - c_a[1], Z - c_a[2]], axis=0)
tt = rel[0] * axis[0] + rel[1] * axis[1] + rel[2] * axis[2]
rr = np.sqrt(rel[0] ** 2 + rel[1] ** 2 + rel[2] ** 2)
u0 = unit(np.array([0, 0, 1.0]) - (np.array([0, 0, 1.0]) @ axis) * axis)   # "arriba" proyectado
v0 = np.cross(axis, u0)
phi = np.arctan2(rel[0] * v0[0] + rel[1] * v0[1] + rel[2] * v0[2], rel[0] * u0[0] + rel[1] * u0[1] + rel[2] * u0[2])
shell = (dist > CLEAR) & (dist <= CLEAR + T_SHELL)
band = (rr > R_a + 3) & (rr < R_a + 32) & (tt > -0.3 * R_a)
cand = shell & band
nb = 12
cnt = np.array([(cand & (np.abs(((phi - (-math.pi + (k + 0.5) * 2 * math.pi / nb) + math.pi) % (2 * math.pi)) - math.pi) < math.pi / nb)).sum() for k in range(nb)])
centers = -math.pi + (np.arange(nb) + 0.5) * 2 * math.pi / nb
order = np.argsort(cnt)[::-1]
chosen = []
for k in order:
    if cnt[k] < 200:
        continue
    if all(abs(((centers[k] - centers[j]) + math.pi) % (2 * math.pi) - math.pi) >= math.radians(80) for j in chosen):
        chosen.append(k)
    if len(chosen) == 3:
        break
print("PARCHES acimut(deg)", [round(math.degrees(centers[k])) for k in chosen], "voxeles/bin", cnt.tolist(), flush=True)
patch = np.zeros(shape, bool)
patch_pts = []
for k in chosen:
    dphi = np.abs(((phi - centers[k]) + math.pi) % (2 * math.pi) - math.pi)
    pm = cand & (dphi < math.radians(24))
    patch |= pm
    idx = np.argwhere(pm)
    # centroide sobre la cara externa (voxel mas lejano de hueso en el parche)
    far = idx[np.argsort(dist[pm])[-max(20, len(idx) // 20):]]
    patch_pts.append(np.array([xs[far[:, 2]].mean(), ys[far[:, 1]].mean(), zs[far[:, 0]].mean()]))

# ---------- 6. tubo guia, puntales y clavijas ----------
t0 = R_a + 34.0
rho2 = rr ** 2 - tt ** 2
rho = np.sqrt(np.maximum(rho2, 0))
tube_out = (tt >= t0) & (tt <= t0 + TUBE_L) & (rho <= TUBE_RO)
bore = (tt >= t0 - 2) & (tt <= t0 + TUBE_L + 2) & (rho <= TUBE_RI)


def capsule(p0, p1, r):
    d = p1 - p0
    L2 = d @ d
    w = np.stack([Xg - p0[0], Y - p0[1], Z - p0[2]], axis=0)
    s = np.clip((w[0] * d[0] + w[1] * d[1] + w[2] * d[2]) / L2, 0, 1)
    dx = w[0] - s * d[0]; dy = w[1] - s * d[1]; dz = w[2] - s * d[2]
    return (dx * dx + dy * dy + dz * dz) <= r * r


struts = np.zeros(shape, bool)
pins = np.zeros(shape, bool)
tree = cKDTree(XR)
pin_info = []
for k, pp in zip(chosen, patch_pts):
    ring = c_a + axis * t0 + (math.cos(centers[k]) * u0 + math.sin(centers[k]) * v0) * (TUBE_RO - 1.5)
    struts |= capsule(ring, pp, STRUT_R)
    # clavija: hacia el hueso mas cercano desde el centroide del parche
    dnear, inear = tree.query(pp)
    dirn = unit(XR[inear] - pp)
    pins |= capsule(pp - dirn * 9.0, pp + dirn * 9.0, PIN_R)
    pin_info.append(dict(punto=pp.round(1).tolist(), direccion=dirn.round(3).tolist(), dist_hueso_mm=round(float(dnear), 1)))

guide = (patch | tube_out | struts) & ~bore & ~pins
guide &= (dist > CLEAR)
lab, nl = ndi.label(guide)
sizes = ndi.sum(guide, lab, range(1, nl + 1))
keep = lab == (int(np.argmax(sizes)) + 1)
removed = int(guide.sum() - keep.sum())
guide = keep
print("GUIA voxeles", int(guide.sum()), "componentes", nl, "descartados", removed, flush=True)


def surface(mask, fn, sigma=0.7, iters=15):
    g = ndi.gaussian_filter(mask.astype(np.float32), sigma)
    fe = vtk.vtkFlyingEdges3D(); fe.SetInputData(to_vtk_image(g)); fe.SetValue(0, 0.5); fe.ComputeNormalsOff(); fe.Update()
    ws = vtk.vtkWindowedSincPolyDataFilter(); ws.SetInputData(fe.GetOutput()); ws.SetNumberOfIterations(iters)
    ws.BoundarySmoothingOff(); ws.NonManifoldSmoothingOn(); ws.NormalizeCoordinatesOn(); ws.Update()
    cl = vtk.vtkCleanPolyData(); cl.SetInputData(ws.GetOutput()); cl.Update()
    o = cl.GetOutput()
    wr = vtk.vtkSTLWriter(); wr.SetFileName(fn); wr.SetInputData(o); wr.SetFileTypeToBinary(); wr.Write()
    fe2 = vtk.vtkFeatureEdges(); fe2.SetInputData(o); fe2.BoundaryEdgesOn(); fe2.NonManifoldEdgesOn(); fe2.FeatureEdgesOff(); fe2.ManifoldEdgesOff(); fe2.Update()
    mp = vtk.vtkMassProperties(); mp.SetInputData(o); mp.Update()
    return dict(tri=int(o.GetNumberOfCells()), bordes_abiertos=int(fe2.GetOutput().GetNumberOfCells()), volumen_mm3=round(mp.GetVolume()))


os_ = {}
os_["guia"] = surface(guide, P + "/guia_copa_acetabular.stl")
# copa de referencia (hemisferio hueco) y eje
Rc = cup_D / 2.0
cup = (rr <= Rc) & (rr >= Rc - 3.0) & (tt >= 0)
os_["copa_referencia"] = surface(cup, P + "/copa_referencia_%dmm.stl" % cup_D, sigma=0.6)
axis_rod = (rho <= 1.2) & (tt >= -R_a) & (tt <= t0 + TUBE_L + 25)
os_["eje_planificado"] = surface(axis_rod, P + "/eje_planificado.stl", sigma=0.5)

# contacto
contact_vox = int(((dist[patch & guide] <= CLEAR + RES * 1.2)).sum())
plan = dict(
    advertencia="Ejercicio academico con datos de cadaver (VSD, CC BY-NC-SA). No es un dispositivo medico ni apto para uso clinico.",
    angulos_objetivo=dict(inclinacion_deg=INCL, anteversion_deg=ANTV, comprobado_inclinacion=round(incl_chk, 2), comprobado_anteversion=round(antv_chk, 2)),
    acetabulo=dict(centro_mm=c_a.round(2).tolist(), radio_mm=round(R_a, 2), copa_diametro_mm=cup_D),
    eje_copa_RAS=axis.round(4).tolist(),
    marcadores_pelvicos=dict(ASIS_R=asis_R.round(1).tolist(), ASIS_L=asis_L.round(1).tolist(), sinfisis=S.round(1).tolist()),
    comprobaciones=dict(vacio_lateral_en_eje=bool(lat_ok), pared_medial_es_hueso=bool(med_ok)),
    parametros=dict(holgura_mm=CLEAR, espesor_parche_mm=T_SHELL, tubo_diam_ext_mm=2 * TUBE_RO, tubo_diam_int_mm=2 * TUBE_RI,
                    tubo_largo_mm=TUBE_L, clavijas_diam_mm=2 * PIN_R, resolucion_voxel_mm=RES),
    parches_acimut_deg=[round(math.degrees(centers[k])) for k in chosen],
    clavijas=pin_info,
    area_contacto_aprox_mm2=round(contact_vox * RES * RES, 0),
    componentes_descartados_voxeles=removed,
    mallas=os_,
    tiempo_s=round(time.time() - t_start, 1))
json.dump(plan, open(P + "/guia_plan.json", "w"), indent=1, ensure_ascii=False)
np.savez(P + "/guia_geom.npz", c_a=c_a, axis=axis, R_a=R_a, t0=t0, x_p=x_p, y_p=y_p, z_p=z_p, asis_R=asis_R, asis_L=asis_L, S=S)
print("PLAN", json.dumps(plan, ensure_ascii=False)[:1800], flush=True)
print("G1_DONE", flush=True)
