import sys, types, time, json
sys.path.insert(0,'deps')
pv=types.ModuleType('pyvista'); pv.core=types.ModuleType('pyvista.core'); sys.modules['pyvista']=pv; sys.modules['pyvista.core']=pv.core
import numpy as np, vtk
from vtk.util.numpy_support import vtk_to_numpy, numpy_to_vtk
import scipy.sparse as sp, scipy.sparse.linalg as spl
import pytetwild
d="C:/Users/Laboratorio/Downloads/femur_vh"
E,NU,F=17000.0,0.30,100.0            # MPa, -, N  (unidades mm-N-MPa)

def read_stl(fn):
    r=vtk.vtkSTLReader(); r.SetFileName(fn); r.Update()
    c=vtk.vtkCleanPolyData(); c.SetInputData(r.GetOutput()); c.Update()
    p=c.GetOutput(); X=vtk_to_numpy(p.GetPoints().GetData()).astype(np.float64)
    T=vtk_to_numpy(p.GetPolys().GetData()).reshape(-1,4)[:,1:].astype(np.int32)
    return X,T

def Dmat():
    l=E*NU/((1+NU)*(1-2*NU)); m=E/(2*(1+NU))
    D=np.zeros((6,6)); D[:3,:3]=l; D[range(3),range(3)]+=2*m; D[3:,3:]=np.eye(3)*m; return D

def assemble(X,T):
    P=X[T]                                   # (n,4,3)
    J=np.stack([P[:,1]-P[:,0],P[:,2]-P[:,0],P[:,3]-P[:,0]],axis=1)   # rows edges
    det=np.linalg.det(J); vol=det/6
    bad=(vol<=0).sum()
    if bad: T[vol<0,1],T[vol<0,2]=T[vol<0,2].copy(),T[vol<0,1].copy(); return assemble(X,T)
    invJ=np.linalg.inv(J)                    # grads of shape fns wrt x: dN/dx = invJ @ dN/dxi
    dNxi=np.array([[-1,-1,-1],[1,0,0],[0,1,0],[0,0,1]],float)   # (4,3)
    G=np.einsum('nji,ki->nkj',invJ,dNxi)  # (n,4,3) verificado con patch test
    B=np.zeros((len(T),6,12))
    for a in range(4):
        gx,gy,gz=G[:,a,0],G[:,a,1],G[:,a,2]
        B[:,0,3*a]=gx; B[:,1,3*a+1]=gy; B[:,2,3*a+2]=gz
        B[:,3,3*a]=gy; B[:,3,3*a+1]=gx
        B[:,4,3*a+1]=gz; B[:,4,3*a+2]=gy
        B[:,5,3*a]=gz; B[:,5,3*a+2]=gx
    D=Dmat()
    Ke=np.einsum('nji,jk,nkl->nil',B,D,B)*vol[:,None,None]
    dof=(3*T[:,:,None]+np.arange(3)).reshape(len(T),12)
    I=np.repeat(dof,12,axis=1).ravel(); Jc=np.tile(dof,(1,12)).ravel()
    K=sp.coo_matrix((Ke.ravel(),(I,Jc)),shape=(3*len(X),3*len(X))).tocsr()
    return K,B,vol,T

def solve(K,fixed_nodes,f):
    n=K.shape[0]; fixed=np.unique((3*fixed_nodes[:,None]+np.arange(3)).ravel())
    free=np.setdiff1d(np.arange(n),fixed)
    Kff=K[free][:,free].tocsc()
    u=np.zeros(n); u[free]=spl.spsolve(Kff,f[free])
    react=(K@u-f)[fixed]; return u,react.reshape(-1,3).sum(0)

def stresses(B,T,u):
    ue=u[(3*T[:,:,None]+np.arange(3)).reshape(len(T),12)]
    s=np.einsum('ij,njk,nk->ni',Dmat(),B,ue)   # sxx syy szz txy tyz tzx
    vm=np.sqrt(0.5*((s[:,0]-s[:,1])**2+(s[:,1]-s[:,2])**2+(s[:,2]-s[:,0])**2)+3*(s[:,3]**2+s[:,4]**2+s[:,5]**2))
    return s,vm

Xs,Ts=read_stl(d+"/femur_L_impresion_1.5mm.stl")
print("STL",len(Xs),len(Ts),flush=True)
out={}
H_=float(sys.argv[1])
for h in (H_,):
    t0=time.time()
    X,T=pytetwild.tetrahedralize(Xs,Ts,edge_length_abs=h,optimize=True,simplify=True,epsilon=2e-3,stop_energy=10.0,coarsen=False,quiet=True)
    T=T.astype(np.int32)
    K,B,vol,T=assemble(X,T)
    zmin,zmax=X[:,2].min(),X[:,2].max()
    fixed=np.where(X[:,2]<zmin+4.0)[0]
    top=np.argmax(X[:,2]); pa=np.where(np.linalg.norm(X-X[top],axis=1)<8.0)[0]
    res={}
    for name,nodes in (("parche_r8mm",pa),("puntual_1nodo",np.array([top]))):
        f=np.zeros(3*len(X)); f[3*nodes+2]=-F/len(nodes)
        u,R=solve(K,fixed,f)
        s,vm=stresses(B,T,u)
        res[name]=dict(umax=float(np.abs(u.reshape(-1,3)).max(0).max()),umag=float(np.linalg.norm(u.reshape(-1,3),axis=1).max()),
                       vm_max=float(vm.max()),vm_p99=float(np.percentile(vm,99)),vm_p95=float(np.percentile(vm,95)),vm_mean=float(np.average(vm,weights=vol)),reaccion_N=R.round(3).tolist())
        if name=="parche_r8mm": keep=(X.copy(),T.copy(),u.copy(),vm.copy(),vol.copy(),s.copy(),fixed.copy(),pa.copy())
    # sección media: área y tensión axial promedio
    zc=0.5*(zmin+zmax); sl=np.abs(X[T].mean(1)[:,2]-zc)<8
    A=vol[sl].sum()/16.0
    sm=keep[5][sl,2]; 
    res["medio"]=dict(area_seccion_mm2=float(A),sigma_axial_teorica_MPa=-F/float(A),sigma_zz_media_fem_MPa=float(np.average(sm,weights=vol[sl])))
    out[h]=dict(nodos=len(X),tets=len(T),tiempo_s=round(time.time()-t0,1),volumen_mm3=float(vol.sum()),**res)
    print("H",h,json.dumps(out[h]),flush=True)
    final=keep
json.dump(out,open(d+"/fea_resultados_h%s.json"%H_,"w"),indent=1)
X,T,u,vm,vol,s,fixed,pa=final
# vtu
ug=vtk.vtkUnstructuredGrid(); pts=vtk.vtkPoints(); pts.SetData(numpy_to_vtk(X)); ug.SetPoints(pts)
ca=vtk.vtkCellArray()
for t in T:
    ca.InsertNextCell(4); [ca.InsertCellPoint(int(i)) for i in t]
ug.SetCells(vtk.VTK_TETRA,ca)
# nodal vm (volume-weighted average)
acc=np.zeros(len(X)); w=np.zeros(len(X))
for k in range(4): np.add.at(acc,T[:,k],vm*vol); np.add.at(w,T[:,k],vol)
vmn=acc/w
for nm,arr in (("desplazamiento_mm",u.reshape(-1,3)),("von_mises_nodal_MPa",vmn)):
    a=numpy_to_vtk(arr); a.SetName(nm); ug.GetPointData().AddArray(a)
a=numpy_to_vtk(vm); a.SetName("von_mises_MPa"); ug.GetCellData().AddArray(a)
wr=vtk.vtkXMLUnstructuredGridWriter(); wr.SetFileName(d+"/fea_femur_L_h%s.vtu"%H_); wr.SetInputData(ug); wr.Write()
gf=vtk.vtkGeometryFilter(); gf.SetInputData(ug); gf.Update()
wp=vtk.vtkXMLPolyDataWriter(); wp.SetFileName(d+"/fea_femur_L_h%s_superficie.vtp"%H_); wp.SetInputData(gf.GetOutput()); wp.Write()
np.save(d+"/fea_bc_h%s.npy"%H_,np.array([fixed.size,pa.size]))
print("DONE",flush=True)
