import sys, types, time, json
sys.path.insert(0, 'C:/Users/Laboratorio/Downloads/femur_vh/deps')
pvm = types.ModuleType('pyvista'); pvm.core = types.ModuleType('pyvista.core')
sys.modules['pyvista'] = pvm; sys.modules['pyvista.core'] = pvm.core
import numpy as np, vtk
from vtk.util.numpy_support import vtk_to_numpy, numpy_to_vtk
import scipy.sparse as sp, scipy.sparse.linalg as spl
from scipy.spatial import cKDTree
import pytetwild

P = "C:/Users/Laboratorio/Downloads/pelvis_guia"
E, NU = 17000.0, 0.30          # MPa (hueso cortical), -
F_TOTAL = 200000.0             # N  (200 kN)
SIGMA_LIM = 130.0              # MPa, referencia aprox. de resistencia cortical (rango 130-200)
H = float(sys.argv[1])


def read_stl(fn):
    r = vtk.vtkSTLReader(); r.SetFileName(fn); r.Update()
    c = vtk.vtkCleanPolyData(); c.SetInputData(r.GetOutput()); c.Update()
    p = c.GetOutput()
    X = vtk_to_numpy(p.GetPoints().GetData()).astype(np.float64)
    T = vtk_to_numpy(p.GetPolys().GetData()).reshape(-1, 4)[:, 1:].astype(np.int32)
    return X, T


def Dmat():
    l = E * NU / ((1 + NU) * (1 - 2 * NU)); m = E / (2 * (1 + NU))
    D = np.zeros((6, 6)); D[:3, :3] = l; D[range(3), range(3)] += 2 * m; D[3:, 3:] = np.eye(3) * m
    return D


def assemble(X, T):
    Pp = X[T]
    J = np.stack([Pp[:, 1] - Pp[:, 0], Pp[:, 2] - Pp[:, 0], Pp[:, 3] - Pp[:, 0]], axis=1)
    vol = np.linalg.det(J) / 6
    neg = vol < 0
    if neg.any():
        T[neg, 1], T[neg, 2] = T[neg, 2].copy(), T[neg, 1].copy()
        return assemble(X, T)
    invJ = np.linalg.inv(J)
    dNxi = np.array([[-1, -1, -1], [1, 0, 0], [0, 1, 0], [0, 0, 1]], float)
    G = np.einsum('nji,ki->nkj', invJ, dNxi)
    B = np.zeros((len(T), 6, 12))
    for a in range(4):
        gx, gy, gz = G[:, a, 0], G[:, a, 1], G[:, a, 2]
        B[:, 0, 3 * a] = gx; B[:, 1, 3 * a + 1] = gy; B[:, 2, 3 * a + 2] = gz
        B[:, 3, 3 * a] = gy; B[:, 3, 3 * a + 1] = gx
        B[:, 4, 3 * a + 1] = gz; B[:, 4, 3 * a + 2] = gy
        B[:, 5, 3 * a] = gz; B[:, 5, 3 * a + 2] = gx
    Ke = np.einsum('nji,jk,nkl->nil', B, Dmat(), B) * vol[:, None, None]
    dof = (3 * T[:, :, None] + np.arange(3)).reshape(len(T), 12)
    I = np.repeat(dof, 12, axis=1).ravel(); Jc = np.tile(dof, (1, 12)).ravel()
    K = sp.coo_matrix((Ke.ravel(), (I, Jc)), shape=(3 * len(X), 3 * len(X))).tocsr()
    return K, B, vol, T


def solve(K, fixed_nodes, f):
    n = K.shape[0]
    fixed = np.unique((3 * fixed_nodes[:, None] + np.arange(3)).ravel())
    free = np.setdiff1d(np.arange(n), fixed)
    u = np.zeros(n)
    u[free] = spl.spsolve(K[free][:, free].tocsc(), f[free])
    react = (K @ u - f)[fixed].reshape(-1, 3).sum(0)
    return u, react


def stresses(B, T, u):
    ue = u[(3 * T[:, :, None] + np.arange(3)).reshape(len(T), 12)]
    s = np.einsum('ij,njk,nk->ni', Dmat(), B, ue)
    vm = np.sqrt(0.5 * ((s[:, 0] - s[:, 1]) ** 2 + (s[:, 1] - s[:, 2]) ** 2 + (s[:, 2] - s[:, 0]) ** 2)
                 + 3 * (s[:, 3] ** 2 + s[:, 4] ** 2 + s[:, 5] ** 2))
    return s, vm


def fit_head(Xf):
    top = Xf[:, 2].max()
    pts = Xf[Xf[:, 2] > top - 50]
    rng = np.random.default_rng(0)
    best = (0, None)
    for _ in range(4000):
        q = pts[rng.choice(len(pts), 4, replace=False)]
        A = np.c_[2 * q, np.ones(4)]
        b = (q ** 2).sum(1)
        try:
            sol = np.linalg.solve(A, b)
        except np.linalg.LinAlgError:
            continue
        c = sol[:3]; R = np.sqrt(sol[3] + c @ c)
        if not (18 < R < 30):
            continue
        n = (np.abs(np.linalg.norm(pts - c, axis=1) - R) < 1.0).sum()
        if n > best[0]:
            best = (n, (c, R))
    c, R = best[1]
    for _ in range(5):  # refinamiento por minimos cuadrados con inliers
        inl = pts[np.abs(np.linalg.norm(pts - c, axis=1) - R) < 1.5]
        A = np.c_[2 * inl, np.ones(len(inl))]
        b = (inl ** 2).sum(1)
        sol = np.linalg.lstsq(A, b, rcond=None)[0]
        c = sol[:3]; R = float(np.sqrt(sol[3] + c @ c))
    return c, R, best[0]


t0 = time.time()
Xh, Th = read_stl(P + "/modelos/Hip_R.stl")
Xs, _ = read_stl(P + "/modelos/Sacrum.stl")
Xl, _ = read_stl(P + "/modelos/Hip_L.stl")
Xf, _ = read_stl(P + "/modelos/Femur_R.stl")
c, R, ninl = fit_head(Xf)
print("CABEZA centro", c.round(1).tolist(), "radio", round(R, 1), "inliers", ninl, flush=True)

X, T = pytetwild.tetrahedralize(Xh, Th, edge_length_abs=H, optimize=True, simplify=True, epsilon=2e-3,
                                stop_energy=10.0, coarsen=False, quiet=True)
T = T.astype(np.int32)
K, B, vol, T = assemble(X, T)
print("MALLA h", H, "nodos", len(X), "tets", len(T), "vol", round(float(vol.sum())), "t", round(time.time() - t0, 1), flush=True)

# apoyos: articulacion sacroiliaca y sinfisis pubica (nodos cercanos a sacro / coxal contralateral)
fixed = None
for dist in (3.0, 4.5, 6.0):
    ts, tl = cKDTree(Xs), cKDTree(Xl)
    si = np.where(ts.query(X)[0] < dist)[0]
    sy = np.where(tl.query(X)[0] < dist)[0]
    if len(si) > 15 and len(sy) > 8:
        fixed = np.union1d(si, sy)
        break
if fixed is None:
    fixed = np.union1d(si, sy)
print("APOYOS sacroiliaca", len(si), "sinfisis", len(sy), "dist", dist, flush=True)

# carga: techo del acetabulo (domo), fuerza radial desde el centro de la cabeza, componente vertical total = 200 kN
d = np.linalg.norm(X - c, axis=1)
rel = (X - c)
cand = np.where((np.abs(d - R) < 3.0) & (rel[:, 2] / np.maximum(d, 1e-9) > 0.25))[0]
r_hat = rel[cand] / d[cand, None]
w = np.maximum(r_hat[:, 2], 0)
fv = (w * r_hat[:, 2]).sum()
scale = F_TOTAL / fv
f = np.zeros(3 * len(X))
for k, i in enumerate(cand):
    f[3 * i:3 * i + 3] += scale * w[k] * r_hat[k]
Fres = f.reshape(-1, 3).sum(0)
print("CARGA nodos", len(cand), "resultante N", Fres.round(0).tolist(), flush=True)

u, R_ = solve(K, fixed, f)
s, vm = stresses(B, T, u)
um = np.linalg.norm(u.reshape(-1, 3), axis=1)
frac = float(vol[vm > SIGMA_LIM].sum() / vol.sum())
res = dict(h=H, nodos=int(len(X)), tets=int(len(T)), volumen_mm3=float(vol.sum()),
           cabeza_centro=c.tolist(), cabeza_radio=float(R), nodos_apoyo=int(len(fixed)), nodos_carga=int(len(cand)),
           fuerza_resultante_N=Fres.tolist(), reaccion_N=R_.tolist(),
           u_max_mm=float(um.max()), vm_max=float(vm.max()), vm_p99=float(np.percentile(vm, 99)),
           vm_p95=float(np.percentile(vm, 95)), vm_media=float(np.average(vm, weights=vol)),
           fraccion_volumen_sobre_130MPa=frac,
           F_para_p99_130MPa_N=float(F_TOTAL * SIGMA_LIM / np.percentile(vm, 99)),
           F_para_media_130MPa_N=float(F_TOTAL * SIGMA_LIM / np.average(vm, weights=vol)))
json.dump(res, open(P + "/fea_pelvis_h%s.json" % H, "w"), indent=1)
print("RES", json.dumps(res), flush=True)

# resultados para visualizacion
ug = vtk.vtkUnstructuredGrid(); pts = vtk.vtkPoints(); pts.SetData(numpy_to_vtk(X)); ug.SetPoints(pts)
ca = vtk.vtkCellArray()
for t in T:
    ca.InsertNextCell(4)
    for i in t:
        ca.InsertCellPoint(int(i))
ug.SetCells(vtk.VTK_TETRA, ca)
acc = np.zeros(len(X)); ww = np.zeros(len(X))
for k in range(4):
    np.add.at(acc, T[:, k], vm * vol); np.add.at(ww, T[:, k], vol)
for nm, arr in (("desplazamiento_mm", u.reshape(-1, 3)), ("von_mises_nodal_MPa", acc / ww)):
    a = numpy_to_vtk(arr); a.SetName(nm); ug.GetPointData().AddArray(a)
a = numpy_to_vtk(vm); a.SetName("von_mises_MPa"); ug.GetCellData().AddArray(a)
wr = vtk.vtkXMLUnstructuredGridWriter(); wr.SetFileName(P + "/fea_pelvis_h%s.vtu" % H); wr.SetInputData(ug); wr.Write()
gf = vtk.vtkGeometryFilter(); gf.SetInputData(ug); gf.Update()
wp = vtk.vtkXMLPolyDataWriter(); wp.SetFileName(P + "/fea_pelvis_h%s_superficie.vtp" % H); wp.SetInputData(gf.GetOutput()); wp.Write()
np.savez(P + "/fea_bc_h%s.npz" % H, fixed=fixed, load=cand, head=c, R=R)
print("DONE", flush=True)
