import slicer, vtk
d="C:/Users/Laboratorio/Downloads/femur_vh"
def bad(p):
    fe=vtk.vtkFeatureEdges(); fe.SetInputData(p); fe.BoundaryEdgesOn(); fe.NonManifoldEdgesOn(); fe.FeatureEdgesOff(); fe.ManifoldEdgesOff(); fe.Update()
    return fe.GetOutput().GetNumberOfCells()
def remesh(poly,h):
    b=poly.GetBounds(); pad=3*h
    dims=[int((b[2*i+1]-b[2*i]+2*pad)/h)+1 for i in range(3)]
    img=vtk.vtkImageData(); img.SetSpacing(h,h,h); img.SetDimensions(dims)
    img.SetOrigin(b[0]-pad,b[2]-pad,b[4]-pad); img.AllocateScalars(vtk.VTK_UNSIGNED_CHAR,1); img.GetPointData().GetScalars().Fill(255)
    st=vtk.vtkPolyDataToImageStencil(); st.SetInputData(poly); st.SetOutputOrigin(img.GetOrigin()); st.SetOutputSpacing(h,h,h); st.SetOutputWholeExtent(img.GetExtent()); st.Update()
    ic=vtk.vtkImageStencil(); ic.SetInputData(img); ic.SetStencilConnection(st.GetOutputPort()); ic.SetBackgroundValue(0); ic.Update()
    g=vtk.vtkImageGaussianSmooth(); g.SetInputData(ic.GetOutput()); g.SetStandardDeviation(0.8); g.Update()
    fl=vtk.vtkFlyingEdges3D(); fl.SetInputData(g.GetOutput()); fl.SetValue(0,127.5); fl.ComputeNormalsOff(); fl.Update()
    ws=vtk.vtkWindowedSincPolyDataFilter(); ws.SetInputData(fl.GetOutput()); ws.SetNumberOfIterations(15); ws.BoundarySmoothingOff(); ws.NonManifoldSmoothingOn(); ws.NormalizeCoordinatesOn(); ws.Update()
    c=vtk.vtkCleanPolyData(); c.SetInputData(ws.GetOutput()); c.Update()
    return c.GetOutput()
for s in ("L","R"):
    m=slicer.util.loadModel(d+"/s016/016/Models/Femur_%s.ply"%s)
    src=m.GetPolyData(); mp0=vtk.vtkMassProperties(); mp0.SetInputData(src); mp0.Update()
    print("RES",s,"orig vol",round(mp0.GetVolume()),flush=True)
    for h in (1.5,2.5,4.0):
        o=remesh(src,h); mp=vtk.vtkMassProperties(); mp.SetInputData(o); mp.Update()
        b=o.GetBounds()
        print("RES",s,"h",h,"cells",o.GetNumberOfCells(),"bad",bad(o),"vol",round(mp.GetVolume()),"len",round(b[5]-b[4],1),flush=True)
        n=slicer.mrmlScene.AddNewNodeByClass("vtkMRMLModelNode","r"); n.SetAndObservePolyData(o)
        slicer.util.saveNode(n,d+"/femur_%s_%s.stl"%(s,{1.5:"impresion_1.5mm",2.5:"fusion_2.5mm",4.0:"fusion_liviano_4mm"}[h]))
slicer.app.quit()
