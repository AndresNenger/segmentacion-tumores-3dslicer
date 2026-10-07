import slicer
d=r"C:\Users\Laboratorio\Downloads\femur_vh"
for s in ("L","R"):
    m=slicer.util.loadModel(d+r"\s016\016\Models\Femur_"+s+".ply")
    b=[0]*6; m.GetBounds(b)
    print("DIM",s,[round(b[i+1]-b[i],1) for i in (0,2,4)],m.GetPolyData().GetNumberOfPoints(),m.GetPolyData().GetNumberOfCells(),flush=True)
    slicer.util.saveNode(m,d.replace("\\","/")+"/femur_"+s+"_TAC016.stl")
slicer.app.quit()
