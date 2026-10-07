import zipfile, numpy as np, vtk
from vtk.util.numpy_support import vtk_to_numpy

P = "C:/Users/Laboratorio/Downloads/pelvis_guia"


def read(fn):
    r = vtk.vtkSTLReader(); r.SetFileName(fn); r.Update()
    c = vtk.vtkCleanPolyData(); c.SetInputData(r.GetOutput()); c.Update()
    t = vtk.vtkTriangleFilter(); t.SetInputData(c.GetOutput()); t.Update()
    p = t.GetOutput()
    X = vtk_to_numpy(p.GetPoints().GetData()).astype(np.float64)
    T = vtk_to_numpy(p.GetPolys().GetData()).reshape(-1, 4)[:, 1:]
    return X, T


def obj_xml(oid, name, X, T):
    v = "".join('<vertex x="%.4f" y="%.4f" z="%.4f"/>' % tuple(p) for p in X)
    t = "".join('<triangle v1="%d" v2="%d" v3="%d"/>' % tuple(f) for f in T)
    return ('<object id="%d" name="%s" type="model"><mesh><vertices>%s</vertices><triangles>%s</triangles></mesh></object>'
            % (oid, name, v, t))


Xg, Tg = read(P + "/imprimir_guia.stl")
Xr, Tr = read(P + "/imprimir_replica_hueso.stl")
model = ('<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" xml:lang="en-US" '
         'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources>'
         + obj_xml(1, "guia_copa_acetabular", Xg, Tg) + obj_xml(2, "replica_hueso_acetabulo", Xr, Tr) +
         '</resources><build>'
         '<item objectid="1" transform="1 0 0 0 1 0 0 0 1 110 110 0"/>'
         '<item objectid="2" transform="1 0 0 0 1 0 0 0 1 110 110 0"/></build></model>')
ct = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
      '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
      '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
with zipfile.ZipFile(P + "/placa_prueba_fisica.3mf", "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("[Content_Types].xml", ct)
    z.writestr("_rels/.rels", rels)
    z.writestr("3D/3dmodel.model", model)
print("3MF ok")
