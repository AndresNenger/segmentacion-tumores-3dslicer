"""Compara dos estudios de resonancia del mismo paciente (MRBrainTumor1 y MRBrainTumor2).

1. Registra el estudio 2 sobre el 1 (BRAINSFit, rígido + afín).
2. Segmenta el tumor en cada estudio con el mismo método semiautomático (semillas + Grow from seeds).
3. Mide volumen y diámetro, y compara: cambio de volumen, solapamiento (Dice) y desplazamiento del centroide.

Ejecutar con la interfaz de Slicer abierta (Grow from seeds falla sin ventana):
    Slicer.exe --python-script comparar.py
Los datos se descargan con el módulo SampleData; ajusta DATA y OUT.
"""
import json, os, sys, traceback
import numpy as np
import slicer, vtk
from scipy import ndimage as ndi

DATA = os.environ.get("DATA_DIR", "C:/Users/Laboratorio/Downloads/tumor_cerebral")
OUT = os.environ.get("OUT_DIR", "C:/Users/Laboratorio/Downloads/repo_tumores/06-comparacion-dos-estudios")
os.makedirs(OUT + "/imagenes", exist_ok=True)


def pump(n=5):
    for _ in range(n):
        slicer.app.processEvents()


def head_mask(a, sp):
    s = ndi.gaussian_filter(a.astype(np.float32), 0.8)
    m = ndi.binary_closing(s > 30, iterations=2)
    for k in range(m.shape[0]):
        m[k] = ndi.binary_fill_holes(m[k])
    lab, n = ndi.label(m)
    sz = ndi.sum(m, lab, range(1, n + 1))
    return lab == (int(np.argmax(sz)) + 1)


def estimate_tumor(a, sp, seed_kji, win_mm=45, recenter_mm=0):
    """Estimación del tumor: umbral relativo (60 % de la intensidad del núcleo) y componente conectada."""
    s = ndi.gaussian_filter(a.astype(np.float32), 0.8)
    head = head_mask(a, sp)
    dh = ndi.distance_transform_edt(head, sampling=sp)
    k0, j0, i0 = seed_kji
    # recentrar en el máximo suavizado cercano a la semilla
    r = [int(recenter_mm / x) for x in sp]
    sl = tuple(slice(max(c - w, 0), c + w + 1) for c, w in zip((k0, j0, i0), r))
    sub = ndi.uniform_filter(s[sl], 5)
    kk, jj, ii = np.unravel_index(np.argmax(sub), sub.shape)
    k0, j0, i0 = sl[0].start + kk, sl[1].start + jj, sl[2].start + ii
    core = float(s[k0 - 1:k0 + 2, j0 - 2:j0 + 3, i0 - 2:i0 + 3].mean())
    kz, jz, iz = np.meshgrid(np.arange(a.shape[0]), np.arange(a.shape[1]), np.arange(a.shape[2]), indexing="ij")
    dist = np.sqrt(((kz - k0) * sp[0]) ** 2 + ((jz - j0) * sp[1]) ** 2 + ((iz - i0) * sp[2]) ** 2)
    m = (s > 0.6 * core) & (dh > 6) & (dist < win_mm)
    lab, n = ndi.label(m)
    t = lab == lab[k0, j0, i0]
    vol_cm3 = t.sum() * float(np.prod(sp)) / 1000
    print("ESTIMACION centro", (int(k0), int(j0), int(i0)), "nucleo", round(core, 1), "vol", round(vol_cm3, 1), "cm3", flush=True)
    if not (2 < vol_cm3 < 80):
        raise RuntimeError("estimacion del tumor fuera de rango (%.1f cm3): revisa la semilla" % vol_cm3)
    return t, head, dh, (k0, j0, i0), core


def seeds_from_estimate(t, head, dh, center, sp):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import seeds
    core = seeds.core_from_estimate(t, center)
    return core, seeds.make_strokes(core, head, dh, sp)


def segment(vol, seg_name, tstrokes, bstrokes):
    a = slicer.util.arrayFromVolume(vol)
    seg = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", seg_name)
    seg.CreateDefaultDisplayNodes()
    seg.SetReferenceImageGeometryParameterFromVolumeNode(vol)
    sg = seg.GetSegmentation()
    tid = sg.AddEmptySegment("Tumor", "Tumor")
    bid = sg.AddEmptySegment("Healthy", "Healthy tissue")
    mt = np.zeros(a.shape, np.uint8)
    mb = np.zeros_like(mt)
    for s_ in tstrokes:
        mt[s_[:, 0], s_[:, 1], s_[:, 2]] = 1
    for s_ in bstrokes:
        mb[s_[:, 0], s_[:, 1], s_[:, 2]] = 1
    slicer.util.updateSegmentBinaryLabelmapFromArray(mt, seg, tid, vol)
    slicer.util.updateSegmentBinaryLabelmapFromArray(mb, seg, bid, vol)
    w = slicer.qMRMLSegmentEditorWidget()
    w.setMRMLScene(slicer.mrmlScene)
    w.setMRMLSegmentEditorNode(slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode"))
    w.setSegmentationNode(seg)
    w.setSourceVolumeNode(vol)
    w.setActiveEffectByName("Grow from seeds")
    e = w.activeEffect()
    e.self().onPreview()
    e.self().onApply()
    w.setCurrentSegmentID(tid)
    w.setActiveEffectByName("Smoothing")
    e = w.activeEffect()
    e.setParameter("SmoothingMethod", "MEDIAN")
    e.setParameter("KernelSizeMm", 3.0)
    e.self().onApply()
    w.setActiveEffectByName("Islands")
    e = w.activeEffect()
    e.setParameter("Operation", "KEEP_LARGEST_ISLAND")
    e.self().onApply()
    w.setActiveEffectByName(None)
    return seg, tid


try:
    v1 = slicer.util.loadVolume(DATA + "/MRBrainTumor1.nrrd")
    v2 = slicer.util.loadVolume(DATA + "/MRBrainTumor2.nrrd")
    v1.SetName("MRBrainTumor1")
    v2.SetName("MRBrainTumor2")
    pump(5)

    # ---------- 1. registro del estudio 2 sobre el 1 ----------
    out_vol = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", "MRBrainTumor2_registrado")
    tr = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode", "T_2_a_1")
    params = dict(fixedVolume=v1.GetID(), movingVolume=v2.GetID(), outputVolume=out_vol.GetID(), linearTransform=tr.GetID(),
                  transformType="Rigid,ScaleVersor3D,Affine", initializeTransformMode="useMomentsAlign",
                  samplingPercentage=0.1, numberOfIterations="1500,1500,1500", interpolationMode="Linear")
    cli = slicer.cli.runSync(slicer.modules.brainsfit, None, params)
    print("REGISTRO", cli.GetStatusString(), flush=True)
    M = vtk.vtkMatrix4x4()
    tr.GetMatrixTransformToParent(M)
    print("TRANSFORM", [[round(M.GetElement(r, c), 3) for c in range(4)] for r in range(3)], flush=True)
    a1 = slicer.util.arrayFromVolume(v1)
    a2r = slicer.util.arrayFromVolume(out_vol)
    # similitud: correlación de intensidades dentro de la cabeza, antes y después
    sp = np.array(v1.GetSpacing())[::-1]
    head1 = head_mask(a1, sp)
    a2o = slicer.util.arrayFromVolume(v2)
    same_shape = a2o.shape == a1.shape
    cc_after = float(np.corrcoef(a1[head1].ravel(), a2r[head1].ravel())[0, 1])
    cc_before = float(np.corrcoef(a1[head1].ravel(), a2o[head1].ravel())[0, 1]) if same_shape else float("nan")
    print("CORRELACION antes %.3f despues %.3f" % (cc_before, cc_after), flush=True)

    # ---------- 2. segmentar el tumor en cada estudio ----------
    seed1 = json.load(open(DATA + "/explora.json"))["centro_kji"]
    t1, hd1, dh1, c1, core1 = estimate_tumor(a1, sp, seed1)
    core_t1, (ts1, bs1) = seeds_from_estimate(t1, hd1, dh1, c1, sp)
    seg1, tid1 = segment(v1, "Seg_estudio1", ts1, bs1)
    m1 = slicer.util.arrayFromSegmentBinaryLabelmap(seg1, tid1, v1).astype(bool)

    # estudio 2 ya en la rejilla del 1: la semilla es la misma posición
    t2, hd2, dh2, c2, core2 = estimate_tumor(a2r, sp, c1, recenter_mm=12)
    core_t2, (ts2, bs2) = seeds_from_estimate(t2, hd2, dh2, c2, sp)
    seg2, tid2 = segment(out_vol, "Seg_estudio2", ts2, bs2)
    m2 = slicer.util.arrayFromSegmentBinaryLabelmap(seg2, tid2, out_vol).astype(bool)

    vox = float(np.prod(sp))
    vol1, vol2 = m1.sum() * vox / 1000, m2.sum() * vox / 1000
    inter = (m1 & m2).sum()
    dice = 2 * inter / (m1.sum() + m2.sum())
    M1, M2 = vtk.vtkMatrix4x4(), vtk.vtkMatrix4x4()
    v1.GetIJKToRASMatrix(M1)
    cen = lambda m: np.array([[M1.GetElement(r, q) for q in range(4)] for r in range(4)]) @ np.append(np.argwhere(m).mean(0)[::-1], 1)
    d_cen = float(np.linalg.norm(cen(m1)[:3] - cen(m2)[:3]))
    res = dict(
        registro=dict(estado=cli.GetStatusString(), correlacion_antes=(None if cc_before != cc_before else round(cc_before, 3)), correlacion_despues=round(cc_after, 3)),
        estudio1=dict(volumen_cm3=round(vol1, 2), intensidad_media=round(float(a1[m1].mean()), 1)),
        estudio2=dict(volumen_cm3=round(vol2, 2), intensidad_media=round(float(a2r[m2].mean()), 1)),
        cambio_volumen_cm3=round(vol2 - vol1, 2), cambio_volumen_pct=round(100 * (vol2 - vol1) / vol1, 1),
        dice=round(float(dice), 3), desplazamiento_centroide_mm=round(d_cen, 2),
        nota="Segmentación semiautomática sin referencia experta; los cambios menores al error del método (≈ 1-2 cm³) no son concluyentes.")
    json.dump(res, open(OUT + "/resultados_comparacion.json", "w"), indent=1, ensure_ascii=False)
    print("RES", json.dumps(res, ensure_ascii=False), flush=True)

    # ---------- 3. imagen comparativa ----------
    from PIL import Image
    k = int(np.argwhere(m1).mean(0)[0])
    w = np.argwhere(m1 | m2)
    j0, i0 = int(w[:, 1].mean()), int(w[:, 2].mean())
    def tile(a, m, k):
        hi = np.percentile(a, 99.5)
        g = (np.clip(a[k] / hi, 0, 1) * 255).astype(np.uint8)
        rgb = np.stack([g, g, g], -1)
        e = m[k] & ~ndi.binary_erosion(m[k])
        rgb[e] = (255, 220, 30)
        return Image.fromarray(rgb[max(j0 - 70, 0):j0 + 70, max(i0 - 70, 0):i0 + 70]).resize((420, 420))
    ov = np.stack([a1[k] * 0 + 0] * 3, -1)
    S = Image.new("RGB", (1260, 420))
    S.paste(tile(a1, m1, k), (0, 0))
    S.paste(tile(a2r, m2, k), (420, 0))
    both = np.zeros(a1.shape[1:] + (3,), np.uint8)
    hi = np.percentile(a1, 99.5)
    g = (np.clip(a1[k] / hi, 0, 1) * 255).astype(np.uint8)
    both[...] = g[..., None]
    both[m1[k] & ~m2[k]] = (255, 60, 60)
    both[m2[k] & ~m1[k]] = (60, 120, 255)
    both[m1[k] & m2[k]] = (255, 220, 30)
    S.paste(Image.fromarray(both[max(j0 - 70, 0):j0 + 70, max(i0 - 70, 0):i0 + 70]).resize((420, 420)), (840, 0))
    S.save(OUT + "/imagenes/comparacion_estudios.png")
    print("IMG ok", flush=True)
except Exception:
    print("ERR", traceback.format_exc(), flush=True)
slicer.app.quit()
