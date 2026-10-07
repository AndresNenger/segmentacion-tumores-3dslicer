"""Genera trazos de semillas (tumor / tejido sano) a partir de la estimacion del tumor.
Devuelve listas de trazos: cada trazo es un array (N, 3) de indices (k, j, i) ordenados como si se pintaran."""
import numpy as np
from scipy import ndimage as ndi


def core_from_estimate(t, center):
    k0, j0, i0 = center
    st = ndi.generate_binary_structure(3, 1)
    o = ndi.binary_opening(t, structure=st, iterations=3)
    lab, n = ndi.label(o)
    L = lab[k0, j0, i0]
    if L == 0:
        sz = ndi.sum(o, lab, range(1, n + 1))
        L = int(np.argmax(sz)) + 1
    return lab == L


def _order(pts, c):
    ang = np.arctan2(pts[:, 1] - c[0], pts[:, 2] - c[1])
    return pts[np.argsort(ang)]


def make_strokes(core, head, dhead, sp):
    w = np.argwhere(core)
    kmin, kmax = w[:, 0].min(), w[:, 0].max()
    kc = int(round(w[:, 0].mean()))
    ks = [kc - 6, kc, kc + 6]
    tumor_strokes, bg_strokes = [], []
    dist_out = ndi.distance_transform_edt(~core, sampling=sp)
    for k in ks:
        sl = core[k]
        if sl.sum() < 20:
            continue
        er = ndi.binary_erosion(sl, iterations=4)
        if er.sum() < 5:
            er = ndi.binary_erosion(sl, iterations=2)
        pts = np.argwhere(er)
        c = pts.mean(0)
        pts3 = np.c_[np.full(len(pts), k), pts]
        tumor_strokes.append(_order(pts3, c))
        ring = (dist_out[k] > 6.0) & (dist_out[k] < 9.0) & head[k] & (dhead[k] > 3.0)
        rp = np.argwhere(ring)
        rp3 = np.c_[np.full(len(rp), k), rp]
        bg_strokes.append(_order(rp3, c))
    # tejido sano por encima y por debajo del tumor
    for k in (int(kmin - round(6 / sp[0])), int(kmax + round(6 / sp[0]))):
        if 0 <= k < core.shape[0]:
            c = w[:, 1:].mean(0)
            jj, ii = np.meshgrid(np.arange(core.shape[1]), np.arange(core.shape[2]), indexing="ij")
            disk = (((jj - c[0]) * sp[1]) ** 2 + ((ii - c[1]) * sp[2]) ** 2 < 18 ** 2) & head[k] & (dhead[k] > 3.0)
            rp = np.argwhere(disk)
            rp3 = np.c_[np.full(len(rp), k), rp]
            bg_strokes.append(_order(rp3, c))
    return tumor_strokes, bg_strokes
