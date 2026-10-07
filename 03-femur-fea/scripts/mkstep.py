import sys, time
sys.path.append('deps_ocp')
import numpy as np, vtk
from vtk.util.numpy_support import vtk_to_numpy
from OCP.gp import gp_Pnt
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace, BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid
from OCP.TopoDS import TopoDS
from OCP.TopAbs import TopAbs_SHELL, TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
from OCP.IFSelect import IFSelect_RetDone
d="C:/Users/Laboratorio/Downloads/femur_vh"
r=vtk.vtkSTLReader(); r.SetFileName(d+"/femur_R_fusion_2.5mm.stl"); r.Update()
c=vtk.vtkCleanPolyData(); c.SetInputData(r.GetOutput()); c.Update(); p=c.GetOutput()
X=vtk_to_numpy(p.GetPoints().GetData()).astype(float); T=vtk_to_numpy(p.GetPolys().GetData()).reshape(-1,4)[:,1:]
print("malla",len(X),"vertices",len(T),"triangulos",flush=True)
t0=time.time(); sew=BRepBuilderAPI_Sewing(1e-4)
pts=[gp_Pnt(*x) for x in X]; n=0
for a,b,cc in T:
    pa,pb,pc=X[a],X[b],X[cc]
    if np.linalg.norm(np.cross(pb-pa,pc-pa))<1e-9: continue
    poly=BRepBuilderAPI_MakePolygon(pts[a],pts[b],pts[cc],True)
    f=BRepBuilderAPI_MakeFace(poly.Wire(),True)
    sew.Add(f.Face()); n+=1
print("caras",n,"t",round(time.time()-t0,1),flush=True)
sew.Perform(); shp=sew.SewedShape()
print("cosido t",round(time.time()-t0,1),"libres",sew.NbFreeEdges(),"multiples",sew.NbMultipleEdges(),flush=True)
from OCP.TopAbs import TopAbs_FACE
best=None; info=[]
ex=TopExp_Explorer(shp,TopAbs_SHELL)
while ex.More():
    sh=TopoDS.Shell(ex.Current())
    nf=0; e2=TopExp_Explorer(sh,TopAbs_FACE)
    while e2.More(): nf+=1; e2.Next()
    so=BRepBuilderAPI_MakeSolid(sh).Solid(); gg=GProp_GProps(); BRepGProp.VolumeProperties_s(so,gg)
    info.append((nf,round(gg.Mass())))
    if best is None or abs(gg.Mass())>abs(best[1]): best=(so,gg.Mass(),nf)
    ex.Next()
print("cascaras (caras,volumen):",sorted(info,reverse=True),flush=True)
solid=best[0]
g=GProp_GProps(); BRepGProp.VolumeProperties_s(solid,g); print("volumen mm3",round(g.Mass()),flush=True)
if g.Mass()<0:
    from OCP.ShapeFix import ShapeFix_Solid
    sf=ShapeFix_Solid(solid); sf.Perform(); solid=TopoDS.Solid(sf.Solid())
    g=GProp_GProps(); BRepGProp.VolumeProperties_s(solid,g); print("volumen corregido",round(g.Mass()),flush=True)
w=STEPControl_Writer(); w.Transfer(solid,STEPControl_AsIs)
st=w.Write(d+"/femur_R.step"); print("STEP",st==IFSelect_RetDone,flush=True)
