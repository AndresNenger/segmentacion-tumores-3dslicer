import slicer, vtk, numpy as np, traceback
from PIL import Image

P = "C:/Users/Laboratorio/Downloads/tumor_cerebral"
try:
    for n in ("MRBrainTumor1", "MRBrainTumor2"):
        v = slicer.util.loadVolume(P + "/%s.nrrd" % n)
        a = slicer.util.arrayFromVolume(v).astype(np.float32)
        M = vtk.vtkMatrix4x4()
        v.GetIJKToRASMatrix(M)
        print("INFO", n, a.shape, [round(s, 3) for s in v.GetSpacing()], "min/max", float(a.min()), float(a.max()),
              "p50/p99", float(np.percentile(a, 50)), float(np.percentile(a, 99)), flush=True)
        print("INFO", n, "IJK2RAS", [[round(M.GetElement(r, c), 3) for c in range(4)] for r in range(3)], flush=True)
        # cortes centrales en las 3 direcciones, normalizados
        hi = np.percentile(a, 99.5)
        def norm(x):
            return (np.clip(x / hi, 0, 1) * 255).astype(np.uint8)
        k, j, i = [s // 2 for s in a.shape]
        # ubicar region mas brillante (probable realce del tumor)
        sm = a.copy()
        from scipy import ndimage as ndi
        sm = ndi.uniform_filter(sm, 9)
        kk, jj, ii = np.unravel_index(np.argmax(sm), sm.shape)
        print("INFO", n, "max realce suavizado en IJK", (int(ii), int(jj), int(kk)), "valor", float(sm[kk, jj, ii]), flush=True)
        ims = [norm(a[kk]), norm(a[:, jj, :])[::-1], norm(a[:, :, ii])[::-1]]
        h = max(x.shape[0] for x in ims)
        canvas = np.zeros((h, sum(x.shape[1] for x in ims)), np.uint8)
        x0 = 0
        for im in ims:
            canvas[:im.shape[0], x0:x0 + im.shape[1]] = im
            x0 += im.shape[1]
        Image.fromarray(canvas).save(P + "/insp_%s.png" % n)
except Exception:
    print("ERR", traceback.format_exc(), flush=True)
slicer.app.quit()
