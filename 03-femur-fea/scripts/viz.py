import slicer, vtk
d="C:/Users/Laboratorio/Downloads/femur_vh"
m=slicer.util.loadModel(d+"/fea_femur_L_h3.5_superficie.vtp")
m.SetName("Femur_L_vonMises")
dn=m.GetDisplayNode()
dn.SetActiveScalarName("von_mises_nodal_MPa"); dn.SetActiveAttributeLocation(vtk.vtkAssignAttribute.POINT_DATA)
dn.SetAndObserveColorNodeID(slicer.util.getNode("Rainbow").GetID() if slicer.mrmlScene.GetFirstNodeByName("Rainbow") else "vtkMRMLColorTableNodeRainbow")
dn.SetScalarRangeFlag(slicer.vtkMRMLDisplayNode.UseManualScalarRange); dn.SetScalarRange(0,2.0); dn.SetScalarVisibility(True)
slicer.util.selectModule("Models")
slicer.app.layoutManager().setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUp3DView)
slicer.util.resetThreeDViews()
# leyenda de color
try:
    cl=slicer.modules.colors.logic()
    v=slicer.app.layoutManager().threeDWidget(0).threeDView().mrmlViewNode()
    lg=slicer.modules.colors.logic().AddDefaultColorLegendDisplayNode(m)
    lg.SetTitleText("Von Mises (MPa) - 100 N compresion"); lg.SetVisibility(True)
except Exception as e: print("leyenda",e)
print("VIZ_OK",flush=True)
