import slicer, vtk, numpy as np
from vtk.util.numpy_support import vtk_to_numpy
from PIL import Image
d=r"C:\Users\Laboratorio\Downloads\femur_vh".replace("\\","/")
imgs=[]
for s in ("L","R"):
    m=slicer.util.loadModel(d+"/s016/016/Models/Femur_"+s+".ply")
    pd=m.GetPolyData()
    tri=vtk.vtkTriangleFilter(); tri.SetInputData(pd); tri.Update()
    q=vtk.vtkQuadricDecimation(); q.SetInputData(tri.GetOutput()); q.SetTargetReduction(1-100000/tri.GetOutput().GetNumberOfCells()); q.Update()
    out=q.GetOutput(); print("DEC",s,out.GetNumberOfCells(),flush=True)
    n=slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode","dec"+s); n.SetAndObservePolyData(out)
    slicer.util.saveNode(n,d+"/femur_"+s+"_TAC016_100k.stl")
    p=vtk_to_numpy(out.GetPoints().GetData())
    row=[]
    for ax in ((0,2),(1,2)):
        a=p[:,list(ax)]; a=(a-a.min(0)); sc=500/ p[:,2].ptp() if False else 500/(np.ptp(p[:,2])+1)
        a=(a*sc).astype(int); im=np.full((520,260),255,np.uint8)
        ok=(a[:,0]<260)&(a[:,1]<520); im[519-a[ok,1],a[ok,0]]=40
        row.append(im)
    imgs.append(np.hstack(row))
Image.fromarray(np.hstack(imgs)).save(d+"/femur_preview.png")
slicer.app.quit()
