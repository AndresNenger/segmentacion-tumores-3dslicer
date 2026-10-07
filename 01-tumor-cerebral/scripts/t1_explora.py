import slicer, vtk, numpy as np, json, traceback
from scipy import ndimage as ndi
from PIL import Image

P = "C:/Users/Laboratorio/Downloads/tumor_cerebral"
try:
    v = slicer.util.loadVolume(P + "/MRBrainTumor1.nrrd")
    a = slicer.util.arrayFromVolume(v).astype(np.float32)
    sp = np.array(v.GetSpacing())[::-1]          # (k, j, i) mm
    s = ndi.gaussian_filter(a, 0.8)
    # cabeza
    head = s > 30
    head = ndi.binary_closing(head, iterations=2)
    for k in range(head.shape[0]):
        head[k] = ndi.binary_fill_holes(head[k])
    lab, n = ndi.label(head)
    sz = ndi.sum(head, lab, range(1, n + 1))
    head = lab == (int(np.argmax(sz)) + 1)
    dhead = ndi.distance_transform_edt(head, sampling=sp)      # profundidad desde la piel (mm)
    # punto semilla aproximado (del mosaico): k=74, j~99, i~133
    k0, j0, i0 = 74, 99, 133
    loc = s[k0 - 1:k0 + 2, j0 - 3:j0 + 4, i0 - 3:i0 + 4]
    print("SEMILLA intensidad media", float(loc.mean()), flush=True)
    # buscar el maximo local de la region para centrar
    win = s[k0 - 6:k0 + 7, j0 - 15:j0 + 16, i0 - 15:i0 + 16]
    kk, jj, ii = np.unravel_index(np.argmax(ndi.uniform_filter(win, 5)), win.shape)
    k0, j0, i0 = k0 - 6 + kk, j0 - 15 + jj, i0 - 15 + ii
    core = float(s[k0 - 1:k0 + 2, j0 - 2:j0 + 3, i0 - 2:i0 + 3].mean())
    print("CENTRO", (int(k0), int(j0), int(i0)), "intensidad nucleo", core, flush=True)
    # cerebro "normal": anillo de 15-25 mm del centro, a > 8 mm de la piel
    kk_, jj_, ii_ = np.meshgrid(np.arange(a.shape[0]), np.arange(a.shape[1]), np.arange(a.shape[2]), indexing="ij")
    dist_c = np.sqrt(((kk_ - k0) * sp[0]) ** 2 + ((jj_ - j0) * sp[1]) ** 2 + ((ii_ - i0) * sp[2]) ** 2)
    ring = (dist_c > 25) & (dist_c < 40) & (dhead > 15)
    print("ANILLO cerebro p25/p50/p75", [float(np.percentile(s[ring], q)) for q in (25, 50, 75)], flush=True)
    # estimacion del tumor por umbral relativo + componente conectada
    for frac in (0.55, 0.6, 0.65, 0.7):
        T = frac * core
        m = (s > T) & (dhead > 6) & (dist_c < 45)
        lab, n = ndi.label(m)
        L = lab[k0, j0, i0]
        if L == 0:
            print("UMBRAL", frac, "semilla fuera", flush=True)
            continue
        t = lab == L
        vol = t.sum() * sp.prod()
        w = np.argwhere(t)
        ext = (w.max(0) - w.min(0) + 1) * sp
        print("UMBRAL frac %.2f T=%.0f vol=%.1f cm3 extension(k,j,i mm)=%s" % (frac, T, vol / 1000, ext.round(1).tolist()), flush=True)
    frac = 0.6
    T = frac * core
    m = (s > T) & (dhead > 6) & (dist_c < 45)
    lab, n = ndi.label(m)
    t = lab == lab[k0, j0, i0]
    np.save(P + "/tumor_estimacion.npy", t)
    np.save(P + "/cabeza.npy", head)
    json.dump(dict(centro_kji=[int(k0), int(j0), int(i0)], nucleo=core, T=T), open(P + "/explora.json", "w"))
    # vista previa
    hi = np.percentile(a, 99.5)
    tiles = []
    w = np.argwhere(t)
    for k in np.linspace(w[:, 0].min() - 2, w[:, 0].max() + 2, 8).astype(int):
        g = (np.clip(a[k] / hi, 0, 1) * 255).astype(np.uint8)
        rgb = np.stack([g, g, g], -1)
        edge = t[k] & ~ndi.binary_erosion(t[k])
        rgb[edge] = (255, 60, 60)
        tiles.append(Image.fromarray(rgb[j0 - 60:j0 + 60, i0 - 60:i0 + 60]).resize((240, 240)))
    sheet = Image.new("RGB", (240 * 8, 240))
    for q, im in enumerate(tiles):
        sheet.paste(im, (q * 240, 0))
    sheet.save(P + "/estimacion_tumor.png")
except Exception:
    print("ERR", traceback.format_exc(), flush=True)
slicer.app.quit()
