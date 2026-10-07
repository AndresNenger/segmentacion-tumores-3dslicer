import json, math, time, traceback
import slicer, vtk, numpy as np
from vtk.util.numpy_support import numpy_to_vtk, vtk_to_numpy
from scipy import ndimage as ndi

P = "C:/Users/Laboratorio/Downloads/tumor_cerebral"
RES = 0.6           # mm, rejilla local isotropica
MARGIN = 10.0       # margen de la ventana de craneotomia alrededor de la proyeccion del tumor (mm)
RIM = 22.0          # ancho del apoyo de la plantilla alrededor de la ventana (mm)
T_SHELL, CLEAR = 3.0, 0.3
MIDLINE_MIN = 15.0  # el punto de entrada debe quedar a >= 15 mm de la linea media (seno sagital superior)
t0 = time.time()


def unit(v):
    return v / np.linalg.norm(v)


def write_surface(mask, org, fn, sigma=0.8, iters=15):
    g = ndi.gaussian_filter(mask.astype(np.float32), sigma)
    img = vtk.vtkImageData()
    img.SetDimensions(mask.shape[2], mask.shape[1], mask.shape[0])
    img.SetSpacing(RES, RES, RES)
    img.SetOrigin(*org)
    img.GetPointData().SetScalars(numpy_to_vtk(g.ravel(), deep=True, array_type=vtk.VTK_FLOAT))
    fe = vtk.vtkFlyingEdges3D(); fe.SetInputData(img); fe.SetValue(0, 0.5); fe.ComputeNormalsOff(); fe.Update()
    ws = vtk.vtkWindowedSincPolyDataFilter(); ws.SetInputData(fe.GetOutput()); ws.SetNumberOfIterations(iters)
    ws.BoundarySmoothingOff(); ws.NonManifoldSmoothingOn(); ws.NormalizeCoordinatesOn(); ws.Update()
    cl = vtk.vtkCleanPolyData(); cl.SetInputData(ws.GetOutput()); cl.Update()
    o = cl.GetOutput()
    wr = vtk.vtkSTLWriter(); wr.SetFileName(fn); wr.SetInputData(o); wr.SetFileTypeToBinary(); wr.Write()
    fe2 = vtk.vtkFeatureEdges(); fe2.SetInputData(o); fe2.BoundaryEdgesOn(); fe2.NonManifoldEdgesOn(); fe2.FeatureEdgesOff(); fe2.ManifoldEdgesOff(); fe2.Update()
    mp = vtk.vtkMassProperties(); mp.SetInputData(o); mp.Update()
    return dict(tri=int(o.GetNumberOfCells()), bordes_abiertos=int(fe2.GetOutput().GetNumberOfCells()), volumen_mm3=round(abs(mp.GetVolume())))


try:
    v = slicer.util.loadVolume(P + "/MRBrainTumor1.nrrd")
    M = vtk.vtkMatrix4x4(); v.GetIJKToRASMatrix(M)
    Mn = np.array([[M.GetElement(r, c) for c in range(4)] for r in range(4)])
    Mi = np.linalg.inv(Mn)
    head_b = np.load(P + "/cabeza.npy")
    # envolvente cerrada de la cabeza: cierre 3D (~3 mm) + relleno de huecos 3D, para que la plantilla no entre en pliegues
    spk = np.array(v.GetSpacing())[::-1]
    pad = 12
    hb = np.pad(head_b, pad)
    sdf = ndi.distance_transform_edt(hb, sampling=spk) - ndi.distance_transform_edt(~hb, sampling=spk)
    sdf = ndi.gaussian_filter(sdf.astype(np.float32), sigma=3.0 / spk)      # paso bajo: quita surcos y bultos < ~6 mm
    head_b = ndi.binary_fill_holes(sdf > 0)[pad:-pad, pad:-pad, pad:-pad]
    lab_, nl_ = ndi.label(head_b)
    head_b = lab_ == (int(np.argmax(ndi.sum(head_b, lab_, range(1, nl_ + 1)))) + 1)
    head = head_b.astype(np.float32)
    tumor = np.load(P + "/tumor_final.npy").astype(np.float32)
    head_s = ndi.gaussian_filter(head, 1.0)
    tumor_s = ndi.gaussian_filter(tumor, 0.7)

    def sample(vol, ras):            # ras: (N,3) -> valores interpolados
        ijk = (Mi[:3, :3] @ ras.T).T + Mi[:3, 3]
        return ndi.map_coordinates(vol, [ijk[:, 2], ijk[:, 1], ijk[:, 0]], order=1, mode="constant", cval=0.0)

    tw = np.argwhere(tumor > 0)
    t_ras = (Mn[:3, :3] @ tw[:, ::-1].T).T + Mn[:3, 3]
    c_t = t_ras.mean(0)
    side = -1.0 if c_t[0] < 0 else 1.0          # RAS: x<0 = izquierda
    print("TUMOR centroide RAS", c_t.round(1).tolist(), "lado", "izquierdo" if side < 0 else "derecho", flush=True)

    # ---------- 1. trayectoria mas corta a la piel, fuera de la linea media ----------
    n = 6000
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n); th = math.pi * (1 + 5 ** 0.5) * i
    dirs = np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)], 1)
    dirs = dirs[dirs[:, 2] > 0.15]
    steps = np.arange(0, 120, 0.5)
    best = None
    for d in dirs:
        pts = c_t + np.outer(steps, d)
        h = sample(head_s, pts)
        out = np.where(h < 0.5)[0]
        if len(out) == 0:
            continue
        L = steps[out[0]]
        e = c_t + d * L
        if side * e[0] < MIDLINE_MIN:        # entrada en el lado del tumor y a >= 15 mm de la linea media
            continue
        if best is None or L < best[0]:
            best = (L, d, e)
    L, d, entry = best
    pts = entry - np.outer(np.arange(0, L, 0.25), d)
    tv = sample(tumor_s, pts)
    depth = float(np.arange(0, L, 0.25)[np.where(tv > 0.5)[0][0]]) if (tv > 0.5).any() else float("nan")
    ang_v = math.degrees(math.acos(d[2]))
    print("TRAYECTORIA entrada", entry.round(1).tolist(), "dir", d.round(3).tolist(), "longitud centro-piel %.1f mm" % L,
          "profundidad piel-tumor %.1f mm" % depth, "angulo con la vertical %.1f" % ang_v, flush=True)

    # ---------- 2. rejilla local ----------
    e1 = unit(np.cross(d, [0, 1.0, 0]) if abs(d[1]) < 0.9 else np.cross(d, [1.0, 0, 0]))
    e2 = np.cross(d, e1)
    # proyeccion del tumor (silueta) sobre el plano perpendicular a d
    uv_t = np.stack([(t_ras - entry) @ e1, (t_ras - entry) @ e2], 1)
    gres = 0.5
    U0, V0 = uv_t.min(0) - 40, uv_t.max(0) + 40
    nu, nv = int((V0[0] - U0[0]) / gres) + 1, int((V0[1] - U0[1]) / gres) + 1
    sil = np.zeros((nu, nv), bool)
    iu = ((uv_t[:, 0] - U0[0]) / gres).astype(int); iv = ((uv_t[:, 1] - U0[1]) / gres).astype(int)
    sil[iu, iv] = True
    sil = ndi.binary_closing(sil, iterations=3)
    sil = ndi.binary_fill_holes(sil)
    # envolvente convexa de la silueta (craneotomia de contorno suave)
    from scipy.spatial import ConvexHull
    from PIL import Image as _Im, ImageDraw as _Dr
    sp_ = np.argwhere(sil)
    hull = ConvexHull(sp_)
    poly = [(float(sp_[q, 1]), float(sp_[q, 0])) for q in hull.vertices]
    him = _Im.new("L", (nv, nu), 0)
    _Dr.Draw(him).polygon(poly, fill=1, outline=1)
    sil_hull = np.array(him, bool)
    sil_tumor = sil.copy()
    sil = sil_hull
    dsil = ndi.distance_transform_edt(~sil, sampling=gres)
    win2d = dsil <= MARGIN
    rim2d = (dsil <= MARGIN + RIM)
    wpts = np.argwhere(win2d) * gres + U0
    win_diam = float(np.max(np.linalg.norm(wpts[:, None, :] - wpts[None, ::50, :], axis=2))) if len(wpts) > 50 else 0.0
    sil_area = float(sil.sum() * gres * gres)
    print("VENTANA area silueta %.0f mm2, diametro maximo ventana ~%.0f mm" % (sil_area, win_diam), flush=True)

    half = 85.0
    N = int(2 * half / RES) + 1
    org = entry - half
    xs = org[0] + RES * np.arange(N); ys = org[1] + RES * np.arange(N); zs = org[2] + RES * np.arange(N)
    Z, Y, X = np.meshgrid(zs.astype(np.float32), ys.astype(np.float32), xs.astype(np.float32), indexing="ij")
    ras = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
    head_l = (sample(head_s, ras) > 0.5).reshape(N, N, N)
    tumor_l = (sample(tumor_s, ras) > 0.5).reshape(N, N, N)
    rel = ras - entry
    tt = (rel @ d).reshape(N, N, N)
    uu = (rel @ e1).reshape(N, N, N); vv = (rel @ e2).reshape(N, N, N)
    del ras, rel
    iu = np.clip(((uu - U0[0]) / gres).astype(int), 0, nu - 1); iv = np.clip(((vv - U0[1]) / gres).astype(int), 0, nv - 1)
    inside_grid = (uu >= U0[0]) & (uu < V0[0]) & (vv >= U0[1]) & (vv < V0[1])
    W = win2d[iu, iv] & inside_grid
    R = rim2d[iu, iv] & inside_grid
    dist_out = ndi.distance_transform_edt(~head_l, sampling=RES).astype(np.float32)
    dist_in = ndi.distance_transform_edt(head_l, sampling=RES).astype(np.float32)
    near = tt > -45                           # solo el lado de la entrada
    shell = (dist_out > CLEAR) & (dist_out <= CLEAR + T_SHELL) & near
    template = shell & R & ~W
    lab, nl = ndi.label(template)
    sz = ndi.sum(template, lab, range(1, nl + 1))
    template = lab == (int(np.argmax(sz)) + 1)
    # contorno de craneotomia sobre la piel (banda de 1.2 mm justo en el borde de la ventana)
    Wd = ndi.binary_dilation(W, iterations=2)
    outline = (dist_out <= 1.2) & (dist_in <= 1.2) & Wd & ~W & near
    # maniqui de prueba: casquete de cuero cabelludo de 15 mm bajo la plantilla
    skin_band = (dist_out <= 1.0) & (dist_in <= 1.0) & R & near
    t_base = float(tt[skin_band].min()) - 6.0                       # base plana 6 mm por debajo del punto mas bajo de la piel
    phantom = head_l & R & (tt >= t_base)
    print("MANIQUI base plana a t = %.1f mm (perpendicular a la trayectoria)" % t_base, flush=True)
    lab, nl = ndi.label(phantom)
    sz = ndi.sum(phantom, lab, range(1, nl + 1))
    phantom = lab == (int(np.argmax(sz)) + 1)

    inside_vox = int((template & head_l).sum())
    sep = float(dsil[iu[template], iv[template]].min())
    print("CONTROL voxeles de plantilla dentro de la cabeza", inside_vox, "| distancia minima plantilla-silueta del tumor (plano) %.1f mm" % sep, flush=True)
    from PIL import Image
    occ = np.zeros((nu, nv), np.int32)
    np.add.at(occ, (iu[template], iv[template]), 1)
    tdep = np.full((nu, nv), np.nan)
    img2 = np.zeros((nu, nv, 3), np.uint8)
    img2[occ > 0] = (30, 190, 180)
    img2[sil] = (120, 100, 20)
    img2[sil_tumor] = (255, 210, 30)
    edge = win2d & ~ndi.binary_erosion(win2d)
    img2[edge] = (255, 40, 40)
    Image.fromarray(img2[::-1]).resize((nv * 2, nu * 2)).save(P + "/debug_proyeccion.png")
    # profundidad (t) de la plantilla: rango por pixel, para detectar capas superpuestas
    tmin = np.full((nu, nv), 1e9); tmax = np.full((nu, nv), -1e9)
    np.minimum.at(tmin, (iu[template], iv[template]), tt[template]); np.maximum.at(tmax, (iu[template], iv[template]), tt[template])
    span = np.where(occ > 0, tmax - tmin, 0)
    print("CONTROL espesor proyectado de la plantilla (t): p50 %.1f p99 %.1f max %.1f mm" % (np.percentile(span[occ > 0], 50), np.percentile(span[occ > 0], 99), span.max()), flush=True)
    mallas = {}
    mallas["plantilla"] = write_surface(template, org, P + "/plantilla_craneotomia.stl")
    mallas["contorno"] = write_surface(outline, org, P + "/contorno_craneotomia.stl", sigma=0.5, iters=8)
    mallas["maniqui"] = write_surface(phantom, org, P + "/maniqui_prueba_cuero_cabelludo.stl")
    mallas["tumor"] = write_surface(tumor_l, org, P + "/tumor_modelo.stl", sigma=0.7)
    # piel completa (rejilla original, para visualizar)
    hs = ndi.gaussian_filter(head, 1.0)
    img = vtk.vtkImageData(); img.SetDimensions(hs.shape[2], hs.shape[1], hs.shape[0]); img.SetSpacing(1, 1, 1)
    img.GetPointData().SetScalars(numpy_to_vtk(hs.ravel(), deep=True, array_type=vtk.VTK_FLOAT))
    fe = vtk.vtkFlyingEdges3D(); fe.SetInputData(img); fe.SetValue(0, 0.5); fe.ComputeNormalsOff(); fe.Update()
    tf = vtk.vtkTransform(); mm = vtk.vtkMatrix4x4(); mm.DeepCopy(M); tf.SetMatrix(mm)
    tpf = vtk.vtkTransformPolyDataFilter(); tpf.SetInputData(fe.GetOutput()); tpf.SetTransform(tf); tpf.Update()
    ws = vtk.vtkWindowedSincPolyDataFilter(); ws.SetInputData(tpf.GetOutput()); ws.SetNumberOfIterations(20); ws.NormalizeCoordinatesOn(); ws.Update()
    dec = vtk.vtkQuadricDecimation(); dec.SetInputData(ws.GetOutput()); dec.SetTargetReduction(0.6); dec.Update()
    nr0 = vtk.vtkPolyDataNormals(); nr0.SetInputData(dec.GetOutput()); nr0.SplittingOff(); nr0.ConsistencyOn(); nr0.AutoOrientNormalsOn(); nr0.Update()
    nr0.GetOutput().GetPointData().SetActiveVectors("Normals")
    wv = vtk.vtkWarpVector(); wv.SetInputData(nr0.GetOutput()); wv.SetScaleFactor(-1.0); wv.Update()
    nr = vtk.vtkPolyDataNormals(); nr.SetInputData(wv.GetOutput()); nr.Update()
    wr = vtk.vtkSTLWriter(); wr.SetFileName(P + "/piel.stl"); wr.SetInputData(nr.GetOutput()); wr.SetFileTypeToBinary(); wr.Write()
    # trayectoria (cilindro de 1 mm)
    line = vtk.vtkLineSource(); line.SetPoint1(*(entry + d * 30)); line.SetPoint2(*c_t); line.Update()
    tube = vtk.vtkTubeFilter(); tube.SetInputData(line.GetOutput()); tube.SetRadius(1.0); tube.SetNumberOfSides(20); tube.CappingOn(); tube.Update()
    wr = vtk.vtkSTLWriter(); wr.SetFileName(P + "/trayectoria.stl"); wr.SetInputData(tube.GetOutput()); wr.SetFileTypeToBinary(); wr.Write()

    plan = dict(
        advertencia="Ejercicio academico con un dato de ejemplo de 3D Slicer. No es un dispositivo medico ni apto para uso clinico.",
        tumor_centroide_ras=c_t.round(2).tolist(), lado="izquierdo" if side < 0 else "derecho",
        entrada_ras=entry.round(2).tolist(), direccion=d.round(4).tolist(), longitud_centro_piel_mm=round(float(L), 1),
        profundidad_piel_superficie_tumor_mm=round(depth, 1), angulo_con_vertical_deg=round(ang_v, 1),
        criterio="trayecto mas corto desde el centro del tumor a la piel, con entrada en el lado del tumor y a >= 15 mm de la linea media",
        margen_ventana_mm=MARGIN, apoyo_alrededor_ventana_mm=RIM, espesor_plantilla_mm=T_SHELL, holgura_mm=CLEAR,
        area_silueta_tumor_mm2=round(sil_area), diametro_max_ventana_mm=round(win_diam),
        mallas=mallas, tiempo_s=round(time.time() - t0, 1))
    json.dump(plan, open(P + "/plan_craneotomia.json", "w"), indent=1, ensure_ascii=False)
    np.savez(P + "/plan_geom.npz", c_t=c_t, entry=entry, d=d, e1=e1, e2=e2)
    print("MALLAS", mallas, flush=True)
    print("T3_DONE", round(time.time() - t0, 1), flush=True)
except Exception:
    print("ERR", traceback.format_exc(), flush=True)
slicer.app.quit()
