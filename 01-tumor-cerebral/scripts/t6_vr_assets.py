"""Recursos para el simulador VR (Meta Quest 3): craneo aproximado, colgajo oseo, voxeles de tumor/tejido sano y datos del plan.
Coordenadas de salida para glTF/three.js: metros, Y arriba: gl = (R, S, -A) / 1000."""
import json, math, time, traceback
import slicer, vtk, numpy as np
from vtk.util.numpy_support import numpy_to_vtk, vtk_to_numpy
from scipy import ndimage as ndi

P = "C:/Users/Laboratorio/Downloads/tumor_cerebral"
SCALP_MM = 4.0          # cuero cabelludo (rango de referencia 3-5 mm)
BONE_MM = 7.5           # hueso frontal (referencia ~6.6-8 mm)
RES = 0.8
t0 = time.time()


def ras2gl(p):
    p = np.asarray(p, float)
    return np.stack([p[..., 0], p[..., 2], -p[..., 1]], -1) / 1000.0


def write_surface(mask, org, fn, sigma=0.8, iters=12):
    g = ndi.gaussian_filter(mask.astype(np.float32), sigma)
    img = vtk.vtkImageData(); img.SetDimensions(mask.shape[2], mask.shape[1], mask.shape[0]); img.SetSpacing(RES, RES, RES); img.SetOrigin(*org)
    img.GetPointData().SetScalars(numpy_to_vtk(g.ravel(), deep=True, array_type=vtk.VTK_FLOAT))
    fe = vtk.vtkFlyingEdges3D(); fe.SetInputData(img); fe.SetValue(0, 0.5); fe.ComputeNormalsOff(); fe.Update()
    ws = vtk.vtkWindowedSincPolyDataFilter(); ws.SetInputData(fe.GetOutput()); ws.SetNumberOfIterations(iters); ws.NormalizeCoordinatesOn(); ws.Update()
    cl = vtk.vtkCleanPolyData(); cl.SetInputData(ws.GetOutput()); cl.Update()
    o = cl.GetOutput()
    w = vtk.vtkSTLWriter(); w.SetFileName(fn); w.SetInputData(o); w.SetFileTypeToBinary(); w.Write()
    return int(o.GetNumberOfCells())


try:
    v = slicer.util.loadVolume(P + "/MRBrainTumor1.nrrd")
    M = vtk.vtkMatrix4x4(); v.GetIJKToRASMatrix(M)
    Mn = np.array([[M.GetElement(r, c) for c in range(4)] for r in range(4)]); Mi = np.linalg.inv(Mn)
    spk = np.array(v.GetSpacing())[::-1]
    # envolvente de la cabeza igual que en t3 (distancia con signo suavizada, sigma 3 mm)
    head_b = np.load(P + "/cabeza.npy")
    pad = 12
    hb = np.pad(head_b, pad)
    sdf = ndi.distance_transform_edt(hb, sampling=spk) - ndi.distance_transform_edt(~hb, sampling=spk)
    sdf = ndi.gaussian_filter(sdf.astype(np.float32), sigma=3.0 / spk)[pad:-pad, pad:-pad, pad:-pad]
    tumor = np.load(P + "/tumor_final.npy")
    geo = np.load(P + "/plan_geom.npz")
    c_t, entry, d, e1, e2 = geo["c_t"], geo["entry"], geo["d"], geo["e1"], geo["e2"]
    plan = json.load(open(P + "/plan_craneotomia.json"))

    def sample(vol, ras, order=1):
        ijk = (Mi[:3, :3] @ ras.T).T + Mi[:3, 3]
        return ndi.map_coordinates(vol, [ijk[:, 2], ijk[:, 1], ijk[:, 0]], order=order, mode="nearest")

    # ---------- craneo aproximado y colgajo oseo en rejilla local ----------
    half = 85.0
    N = int(2 * half / RES) + 1
    org = entry - half
    xs = org[0] + RES * np.arange(N); ys = org[1] + RES * np.arange(N); zs = org[2] + RES * np.arange(N)
    Z, Y, X = np.meshgrid(zs.astype(np.float32), ys.astype(np.float32), xs.astype(np.float32), indexing="ij")
    ras = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
    depth = sample(sdf, ras).reshape(N, N, N)                 # mm bajo la piel (>0 dentro)
    rel = ras - entry
    tt = (rel @ d).reshape(N, N, N); uu = (rel @ e1).reshape(N, N, N); vv = (rel @ e2).reshape(N, N, N)
    dist_entry = np.linalg.norm(rel, axis=1).reshape(N, N, N)
    del ras, rel
    skull = (depth >= SCALP_MM) & (depth <= SCALP_MM + BONE_MM) & (dist_entry <= 75.0) & (tt > -60)
    # ventana de craneotomia: misma construccion que t3 (envolvente convexa de la silueta + 10 mm)
    tw = np.argwhere(tumor)
    t_ras = (Mn[:3, :3] @ tw[:, ::-1].T).T + Mn[:3, 3]
    uv_t = np.stack([(t_ras - entry) @ e1, (t_ras - entry) @ e2], 1)
    gres = 0.5
    U0, V0 = uv_t.min(0) - 40, uv_t.max(0) + 40
    nu, nv = int((V0[0] - U0[0]) / gres) + 1, int((V0[1] - U0[1]) / gres) + 1
    sil = np.zeros((nu, nv), bool)
    sil[((uv_t[:, 0] - U0[0]) / gres).astype(int), ((uv_t[:, 1] - U0[1]) / gres).astype(int)] = True
    sil = ndi.binary_fill_holes(ndi.binary_closing(sil, iterations=3))
    from scipy.spatial import ConvexHull
    from PIL import Image, ImageDraw
    sp_ = np.argwhere(sil); hull = ConvexHull(sp_)
    him = Image.new("L", (nv, nu), 0)
    ImageDraw.Draw(him).polygon([(float(sp_[q, 1]), float(sp_[q, 0])) for q in hull.vertices], fill=1, outline=1)
    win2d = ndi.distance_transform_edt(~np.array(him, bool), sampling=gres) <= plan["margen_ventana_mm"]
    iu = np.clip(((uu - U0[0]) / gres).astype(int), 0, nu - 1); iv = np.clip(((vv - U0[1]) / gres).astype(int), 0, nv - 1)
    inside = (uu >= U0[0]) & (uu < V0[0]) & (vv >= U0[1]) & (vv < V0[1])
    W = win2d[iu, iv] & inside & (tt > -45)
    flap = skull & W
    skull_rest = skull & ~W
    tri = {}
    tri["craneo"] = write_surface(skull_rest, org, P + "/vr_craneo_aprox.stl")
    tri["colgajo"] = write_surface(flap, org, P + "/vr_colgajo_oseo.stl")
    print("CRANEO", tri, "colgajo vol cm3 %.1f" % (flap.sum() * RES ** 3 / 1000), flush=True)

    # ---------- voxeles de tumor y de tejido sano (anillo de 3 mm) ----------
    VS = 1.6
    lo = t_ras.min(0) - 6; hi = t_ras.max(0) + 6
    gx = np.arange(lo[0], hi[0], VS); gy = np.arange(lo[1], hi[1], VS); gz = np.arange(lo[2], hi[2], VS)
    GZ, GY, GX = np.meshgrid(gz, gy, gx, indexing="ij")
    pts = np.stack([GX.ravel(), GY.ravel(), GZ.ravel()], 1)
    tum_f = ndi.gaussian_filter(tumor.astype(np.float32), 0.5)
    dist_t = ndi.distance_transform_edt(~tumor, sampling=spk)
    tv = sample(tum_f, pts) > 0.5
    dv = sample(dist_t.astype(np.float32), pts)
    dep = sample(sdf, pts)
    healthy = (~tv) & (dv > 0) & (dv <= 3.0) & (dep > SCALP_MM + BONE_MM + 1.0)
    # el corredor de abordaje (entre la duramadre y el tumor, dentro de la ventana) no cuenta como tejido a preservar
    relp = pts - entry
    up_ = relp @ e1; vp_ = relp @ e2
    iup = np.clip(((up_ - U0[0]) / gres).astype(int), 0, nu - 1); ivp = np.clip(((vp_ - U0[1]) / gres).astype(int), 0, nv - 1)
    in_win = win2d[iup, ivp] & (up_ >= U0[0]) & (up_ < V0[0]) & (vp_ >= U0[1]) & (vp_ < V0[1])
    above = ((pts - c_t) @ d) > 0
    healthy &= ~(in_win & above)
    tum_pts, hea_pts = pts[tv], pts[healthy]
    print("VOXELES tumor", len(tum_pts), "(%.1f cm3)" % (len(tum_pts) * VS ** 3 / 1000), "sano", len(hea_pts), flush=True)

    shift_dir = -d              # hundimiento del cerebro alejandose de la craneotomia (direccion opuesta al abordaje)
    data = dict(
        aviso="Academic exercise with 3D Slicer sample data MRBrainTumor1. Not a medical device. Not for clinical use.",
        unidades="metros, Y arriba (glTF): gl = (R, S, -A)/1000",
        voxel_mm=VS,
        tumor_voxels=np.round(ras2gl(tum_pts), 5).tolist(),
        healthy_voxels=np.round(ras2gl(hea_pts), 5).tolist(),
        entry=ras2gl(entry).round(5).tolist(), target=ras2gl(c_t).round(5).tolist(),
        approach_dir=ras2gl(d * 1000).round(5).tolist(), shift_dir=ras2gl(shift_dir * 1000).round(5).tolist(),
        plan=dict(volumen_tumor_cm3=16.94, feret_mm=39.8, profundidad_mm=plan["profundidad_piel_superficie_tumor_mm"],
                  ventana_mm=plan["diametro_max_ventana_mm"], margen_mm=plan["margen_ventana_mm"], angulo_vertical=plan["angulo_con_vertical_deg"]),
        capas_mm=dict(cuero_cabelludo=SCALP_MM, hueso=BONE_MM),
    )
    # contorno de craneotomia como polilinea (puntos de la superficie del contorno)
    r = vtk.vtkSTLReader(); r.SetFileName(P + "/contorno_craneotomia.stl"); r.Update()
    op = vtk_to_numpy(r.GetOutput().GetPoints().GetData()).astype(float)
    ang = np.arctan2((op - entry) @ e2, (op - entry) @ e1)
    order = np.argsort(ang)
    op = op[order][::max(len(op) // 360, 1)]
    data["outline"] = np.round(ras2gl(op), 5).tolist()
    json.dump(data, open(P + "/vr_data.json", "w"))
    print("JSON vr_data.json", round(len(json.dumps(data)) / 1e6, 2), "MB", flush=True)
    print("T6_DONE", round(time.time() - t0, 1), flush=True)
except Exception:
    print("ERR", traceback.format_exc(), flush=True)
slicer.app.quit()
