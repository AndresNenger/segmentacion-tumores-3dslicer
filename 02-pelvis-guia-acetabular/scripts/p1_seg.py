import slicer, vtk, numpy as np, traceback, json
from scipy import ndimage as ndi
from vtk.util.numpy_support import numpy_to_vtk, vtk_to_numpy

P = "C:/Users/Laboratorio/Downloads/pelvis_guia"
B = "C:/Users/Laboratorio/Downloads/femur_vh/s016/016/SMIR.Lower_limb.095Y.F.CT.476/"
try:
    v = slicer.util.loadVolume(B + "SMIR.Lower_limb.095Y.F.CT.476.nrrd")
    seg = slicer.util.loadSegmentation(B + "SMIR.Lower_limb.095Y.F.CT.476-Pelvis-Thighs_Reconstruction.seg.nrrd")
    ct = slicer.util.arrayFromVolume(v)
    M = vtk.vtkMatrix4x4()
    v.GetIJKToRASMatrix(M)
    Mn = np.array([[M.GetElement(r, c) for c in range(4)] for r in range(4)])
    sg = seg.GetSegmentation()
    ids = {sg.GetNthSegment(i).GetName(): sg.GetNthSegmentID(i) for i in range(sg.GetNumberOfSegments())}
    stats = {}

    def surface(mask, name):
        # recorte para acelerar
        w = np.argwhere(mask)
        lo = np.maximum(w.min(0) - 6, 0)
        hi = np.minimum(w.max(0) + 7, mask.shape)
        sub = mask[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]].astype(np.float32)
        sub = ndi.gaussian_filter(sub, 0.9)
        img = vtk.vtkImageData()
        img.SetDimensions(sub.shape[2], sub.shape[1], sub.shape[0])
        arr = numpy_to_vtk(sub.ravel(), deep=True, array_type=vtk.VTK_FLOAT)
        img.GetPointData().SetScalars(arr)
        fe = vtk.vtkFlyingEdges3D()
        fe.SetInputData(img)
        fe.SetValue(0, 0.5)
        fe.ComputeNormalsOff()
        fe.Update()
        pts = vtk_to_numpy(fe.GetOutput().GetPoints().GetData()).astype(np.float64)
        # (x=i, y=j, z=k) del subvolumen -> IJK global
        ijk = pts + np.array([lo[2], lo[1], lo[0]])
        ras = (Mn[:3, :3] @ ijk.T).T + Mn[:3, 3]
        po = fe.GetOutput()
        vp = vtk.vtkPoints()
        vp.SetData(numpy_to_vtk(ras, deep=True))
        po2 = vtk.vtkPolyData()
        po2.SetPoints(vp)
        po2.SetPolys(po.GetPolys())
        ws = vtk.vtkWindowedSincPolyDataFilter()
        ws.SetInputData(po2)
        ws.SetNumberOfIterations(25)
        ws.BoundarySmoothingOff()
        ws.NonManifoldSmoothingOn()
        ws.NormalizeCoordinatesOn()
        ws.Update()
        dec = vtk.vtkQuadricDecimation()
        dec.SetInputData(ws.GetOutput())
        dec.SetTargetReduction(0.5)
        dec.Update()
        cl = vtk.vtkCleanPolyData()
        cl.SetInputData(dec.GetOutput())
        cl.Update()
        out = cl.GetOutput()
        fe2 = vtk.vtkFeatureEdges()
        fe2.SetInputData(out)
        fe2.BoundaryEdgesOn()
        fe2.NonManifoldEdgesOn()
        fe2.FeatureEdgesOff()
        fe2.ManifoldEdgesOff()
        fe2.Update()
        mp = vtk.vtkMassProperties()
        mp.SetInputData(out)
        mp.Update()
        wr = vtk.vtkSTLWriter()
        wr.SetFileName(P + "/modelos/%s.stl" % name)
        wr.SetInputData(out)
        wr.SetFileTypeToBinary()
        wr.Write()
        b = out.GetBounds()
        return dict(tri=out.GetNumberOfCells(), bordes_abiertos=fe2.GetOutput().GetNumberOfCells(),
                    volumen_mm3=round(mp.GetVolume()), dims_mm=[round(b[1] - b[0], 1), round(b[3] - b[2], 1), round(b[5] - b[4], 1)])

    clean = {}
    for name in ("Hip_R", "Hip_L", "Sacrum"):
        m = slicer.util.arrayFromSegmentBinaryLabelmap(seg, ids[name], v).astype(bool)
        n0 = int(m.sum())
        lab, k = ndi.label(m)
        sizes = ndi.sum(m, lab, range(1, k + 1))
        m = lab == (int(np.argmax(sizes)) + 1)
        islas = int(k)
        m = ndi.binary_closing(m, iterations=1)
        m = ndi.binary_fill_holes(m)
        for z in range(m.shape[0]):
            m[z] = ndi.binary_fill_holes(m[z])
        clean[name] = m
        s = surface(m, name)
        s.update(vox_original=n0, vox_limpio=int(m.sum()), islas_originales=islas)
        stats[name] = s
        print("STAT", name, s, flush=True)
    # Femur derecho (para ubicar la cabeza femoral en el analisis)
    mf = slicer.util.arrayFromSegmentBinaryLabelmap(seg, ids["Femur_R"], v).astype(bool)
    lab, k = ndi.label(mf)
    sizes = ndi.sum(mf, lab, range(1, k + 1))
    mf = lab == (int(np.argmax(sizes)) + 1)
    stats["Femur_R"] = surface(mf, "Femur_R")
    print("STAT Femur_R", stats["Femur_R"], flush=True)
    json.dump(stats, open(P + "/segmentacion_estadisticas.json", "w"), indent=1)
    print("P1_DONE", flush=True)
except Exception:
    print("ERR", traceback.format_exc(), flush=True)
slicer.app.quit()
