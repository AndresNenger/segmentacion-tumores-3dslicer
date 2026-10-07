import sys, json, traceback
sys.path.insert(0, "C:/Users/Laboratorio/Downloads/tumor_cerebral")
import slicer, vtk, numpy as np
from scipy import ndimage as ndi
from PIL import Image
import seeds

P = "C:/Users/Laboratorio/Downloads/tumor_cerebral"
try:
    v = slicer.util.loadVolume(P + "/MRBrainTumor1.nrrd")
    v.SetName("MRBrainTumor1")
    a = slicer.util.arrayFromVolume(v).astype(np.float32)
    sp = np.array(v.GetSpacing())[::-1]
    ex = json.load(open(P + "/explora.json"))
    t = np.load(P + "/tumor_estimacion.npy")
    head = np.load(P + "/cabeza.npy")
    dhead = ndi.distance_transform_edt(head, sampling=sp)
    core = seeds.core_from_estimate(t, ex["centro_kji"])
    print("NUCLEO vol cm3", round(core.sum() * sp.prod() / 1000, 2), flush=True)
    ts, bs = seeds.make_strokes(core, head, dhead, sp)
    print("TRAZOS tumor", len(ts), [len(x) for x in ts], "fondo", len(bs), [len(x) for x in bs], flush=True)

    seg = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", "Segmentacion")
    seg.CreateDefaultDisplayNodes()
    seg.SetReferenceImageGeometryParameterFromVolumeNode(v)
    sg = seg.GetSegmentation()
    tid = sg.AddEmptySegment("Tumor", "Tumor")
    bid = sg.AddEmptySegment("Tejido_sano", "Tejido_sano")
    sg.GetSegment(tid).SetColor(1.0, 0.85, 0.1)
    sg.GetSegment(bid).SetColor(0.2, 0.6, 1.0)
    mt = np.zeros(a.shape, np.uint8)
    mb = np.zeros(a.shape, np.uint8)
    for s_ in ts:
        mt[s_[:, 0], s_[:, 1], s_[:, 2]] = 1
    for s_ in bs:
        mb[s_[:, 0], s_[:, 1], s_[:, 2]] = 1
    slicer.util.updateSegmentBinaryLabelmapFromArray(mt, seg, tid, v)
    slicer.util.updateSegmentBinaryLabelmapFromArray(mb, seg, bid, v)

    w = slicer.qMRMLSegmentEditorWidget()
    w.setMRMLScene(slicer.mrmlScene)
    en = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")
    w.setMRMLSegmentEditorNode(en)
    w.setSegmentationNode(seg)
    try:
        w.setSourceVolumeNode(v)
    except AttributeError:
        w.setMasterVolumeNode(v)
    w.setActiveEffectByName("Grow from seeds")
    eff = w.activeEffect()
    eff.self().onPreview()
    eff.self().onApply()
    print("GROW ok", flush=True)
    w.setCurrentSegmentID(tid)
    print("PASO seleccion", flush=True)
    w.setActiveEffectByName("Smoothing")
    eff = w.activeEffect()
    eff.setParameter("SmoothingMethod", "MEDIAN")
    eff.setParameter("KernelSizeMm", 3.0)
    print("PASO suavizado inicio", flush=True)
    eff.self().onApply()
    print("PASO suavizado ok", flush=True)
    w.setActiveEffectByName("Islands")
    eff = w.activeEffect()
    eff.setParameter("Operation", "KEEP_LARGEST_ISLAND")
    print("PASO islas inicio", flush=True)
    eff.self().onApply()
    print("PASO islas ok", flush=True)
    w.setActiveEffectByName(None)
    tumor = slicer.util.arrayFromSegmentBinaryLabelmap(seg, tid, v).astype(bool)
    print("TUMOR vol cm3", round(tumor.sum() * sp.prod() / 1000, 3), flush=True)

    # referencia de tejido cerebral sano: esfera de 6 mm en sustancia blanca contralateral
    k0, j0, i0 = ex["centro_kji"]
    sg.RemoveSegment(bid)
    rid = sg.AddEmptySegment("Referencia_SB", "Referencia_sustancia_blanca_derecha")
    sg.GetSegment(rid).SetColor(0.3, 0.9, 0.4)
    kk, jj, ii = np.meshgrid(np.arange(a.shape[0]), np.arange(a.shape[1]), np.arange(a.shape[2]), indexing="ij")
    # punto contralateral: 30 mm al lado opuesto de la linea media, 10 mm posterior, mismo nivel
    # busqueda automatica: zona mas homogenea (sustancia blanca) del hemisferio derecho, profunda
    M = vtk.vtkMatrix4x4()
    v.GetIJKToRASMatrix(M)
    Mn = np.array([[M.GetElement(r, q) for q in range(4)] for r in range(4)])
    sm = ndi.uniform_filter(a, (5, 9, 9))
    sq = ndi.uniform_filter(a * a, (5, 9, 9))
    sd_loc = np.sqrt(np.maximum(sq - sm * sm, 0))
    best = None
    for k_ in range(int(k0) - 8, int(k0) + 9, 2):
        for j_ in range(40, 200, 3):
            for i_ in range(40, 220, 3):
                x, y, z = (Mn[:3, :3] @ [i_, j_, k_]) + Mn[:3, 3]
                if not (18 < x < 40) or not (-25 < y < 25) or dhead[k_, j_, i_] < 30:
                    continue
                sc = sd_loc[k_, j_, i_]
                if sm[k_, j_, i_] > 80 and (best is None or sc < best[0]):
                    best = (sc, k_, j_, i_)
    _, k_best, j_ref, i_ref = best
    k0 = k_best
    k_ref = int(k0)
    refm = (((kk - k_ref) * sp[0]) ** 2 + ((jj - j_ref) * sp[1]) ** 2 + ((ii - i_ref) * sp[2]) ** 2) < 6 ** 2
    slicer.util.updateSegmentBinaryLabelmapFromArray(refm.astype(np.uint8), seg, rid, v)
    print("REF punto kji", (k_ref, j_ref, i_ref), "media", float(a[refm].mean()), "sd", float(a[refm].std()), flush=True)

    import SegmentStatistics
    lg = SegmentStatistics.SegmentStatisticsLogic()
    pn = lg.getParameterNode()
    pn.SetParameter("Segmentation", seg.GetID())
    pn.SetParameter("ScalarVolume", v.GetID())
    for f in ("feret_diameter_mm", "surface_area_mm2", "roundness", "flatness", "elongation", "principal_moments", "centroid_ras"):
        pn.SetParameter("LabelmapSegmentStatisticsPlugin.%s.enabled" % f, "True")
    lg.computeStatistics()
    stt = lg.getStatistics()
    out = {}
    for sid in stt["SegmentIDs"]:
        name = sg.GetSegment(sid).GetName()
        d = {}
        for key in stt["MeasurementInfo"].keys():
            if (sid, key) in stt:
                val = stt[sid, key]
                try:
                    d[key] = float(val) if not isinstance(val, (list, tuple)) else [float(x) for x in val]
                except Exception:
                    d[key] = str(val)
        out[name] = d
    json.dump(out, open(P + "/estadisticas_segmentos.json", "w"), indent=1)
    for name, d in out.items():
        print("STATS", name, {k: (round(x, 2) if isinstance(x, float) else x) for k, x in d.items() if any(s in k for s in ("volume_cm3", "mean", "stdev", "median", "feret", "roundness", "elongation", "flatness", "surface_area", "min", "max", "centroid"))}, flush=True)
    slicer.util.saveNode(seg, P + "/segmentacion_tumor.seg.nrrd")
    np.save(P + "/tumor_final.npy", tumor)
    # vista previa
    hi = np.percentile(a, 99.5)
    w_ = np.argwhere(tumor)
    jc, ic = w_[:, 1].mean(), w_[:, 2].mean()
    tiles = []
    for k in np.linspace(w_[:, 0].min() - 1, w_[:, 0].max() + 1, 8).astype(int):
        g = (np.clip(a[k] / hi, 0, 1) * 255).astype(np.uint8)
        rgb = np.stack([g, g, g], -1)
        e = tumor[k] & ~ndi.binary_erosion(tumor[k])
        rgb[e] = (255, 220, 30)
        rgb[mt[k] > 0] = (255, 120, 0)
        rgb[mb[k] > 0] = (60, 140, 255)
        jc_, ic_ = int(jc), int(ic)
        tiles.append(Image.fromarray(rgb[max(jc_ - 60, 0):jc_ + 60, max(ic_ - 60, 0):ic_ + 60]).resize((240, 240)))
    sheet = Image.new("RGB", (240 * 8, 240))
    for q, im in enumerate(tiles):
        sheet.paste(im, (q * 240, 0))
    sheet.save(P + "/segmentacion_preview.png")
    print("T2_DONE", flush=True)
except Exception:
    print("ERR", traceback.format_exc(), flush=True)
slicer.app.quit()
