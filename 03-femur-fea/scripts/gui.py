import slicer, vtk, time, qt
d="C:/Users/Laboratorio/Downloads/femur_vh"
def pause(s=1.5):
    t=time.time()
    while time.time()-t<s: slicer.app.processEvents()
def log(msg):
    print("STEP",msg,flush=True); slicer.util.showStatusMessage(msg,0); pause(1.0)
slicer.util.selectModule("Models")
lm=slicer.app.layoutManager(); lm.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUp3DView)
log("Cargando fémur izquierdo (600k triángulos)")
L=slicer.util.loadModel(d+"/s016/016/Models/Femur_L.ply"); L.GetDisplayNode().SetColor(0.9,0.85,0.7)
slicer.util.resetThreeDViews(); pause(2)
log("Cargando fémur derecho")
R=slicer.util.loadModel(d+"/s016/016/Models/Femur_R.ply"); R.GetDisplayNode().SetColor(0.7,0.85,0.9)
slicer.util.resetThreeDViews(); pause(2)
def check(n,name):
    tri=vtk.vtkTriangleFilter(); tri.SetInputData(n.GetPolyData()); tri.Update()
    fe=vtk.vtkFeatureEdges(); fe.SetInputData(tri.GetOutput())
    fe.BoundaryEdgesOn(); fe.NonManifoldEdgesOn(); fe.FeatureEdgesOff(); fe.ManifoldEdgesOff(); fe.Update()
    mp=vtk.vtkMassProperties(); mp.SetInputData(tri.GetOutput()); mp.Update()
    b=[0]*6; n.GetBounds(b)
    print("CHECK",name,"bordes abiertos/no-manifold:",fe.GetOutput().GetNumberOfCells(),"volumen mm3:",round(mp.GetVolume()),"largo mm:",round(b[5]-b[4],1),flush=True)
log("Revisando que la malla sea estanca (watertight)")
check(L,"L"); check(R,"R")
def deci(n,name,target):
    tri=vtk.vtkTriangleFilter(); tri.SetInputData(n.GetPolyData()); tri.Update()
    q=vtk.vtkQuadricDecimation(); q.SetInputData(tri.GetOutput())
    q.SetTargetReduction(1-target/tri.GetOutput().GetNumberOfCells()); q.Update()
    out=q.GetOutput()
    node=slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode","Femur_%s_FEA"%name); node.SetAndObservePolyData(out); node.CreateDefaultDisplayNodes()
    return node
log("Simplificando a ~15k triángulos para Fusion (conversión a sólido)")
FL=deci(L,"L",15000); FR=deci(R,"R",15000)
L.GetDisplayNode().SetVisibility(False); R.GetDisplayNode().SetVisibility(False)
FL.GetDisplayNode().SetColor(0.9,0.85,0.7); FR.GetDisplayNode().SetColor(0.7,0.85,0.9)
FL.GetDisplayNode().SetRepresentation(1); FR.GetDisplayNode().SetRepresentation(1)  # wireframe-ish view
FL.GetDisplayNode().SetEdgeVisibility(True); FR.GetDisplayNode().SetEdgeVisibility(True)
FL.GetDisplayNode().SetRepresentation(2); FR.GetDisplayNode().SetRepresentation(2)
slicer.util.resetThreeDViews(); pause(2)
check(FL,"L_15k"); check(FR,"R_15k")
log("Guardando STL para Fusion")
slicer.util.saveNode(FL,d+"/femur_L_FEA_15k.stl"); slicer.util.saveNode(FR,d+"/femur_R_FEA_15k.stl")
log("Listo. STL guardados en femur_vh")
print("DONE",flush=True)
