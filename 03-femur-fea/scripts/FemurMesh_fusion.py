# Inserta el femur (STL, mm) y lo convierte a cuerpo solido. NO probado en Fusion: si un paso falla,
# el mensaje indica cual; el resto se hace a mano (Insertar > Insertar malla; clic derecho > Convertir malla).
import adsk.core, adsk.fusion, traceback

STL = r"C:\Users\Laboratorio\Downloads\femur_vh\femur_L_fusion_2.5mm.stl"

def run(context):
    ui = None
    try:
        app = adsk.core.Application.get(); ui = app.userInterface
        design = adsk.fusion.Design.cast(app.activeProduct)
        if not design:
            ui.messageBox("Abre un diseno (Archivo > Nuevo diseno) y ejecuta de nuevo."); return
        root = design.rootComponent
        # 1) insertar malla en milimetros
        mesh = root.meshBodies.add(STL, adsk.fusion.MeshUnits.MillimeterMeshUnit)
        ui.messageBox("Malla insertada: %s" % mesh.name)
        # 2) convertir a solido (facetado)
        try:
            feats = root.features.meshConvertFeatures
            inp = feats.createInput(mesh.meshBody if hasattr(mesh, "meshBody") else mesh)
            try: inp.meshConvertMethodType = adsk.fusion.MeshConvertMethodTypes.FacetedMeshConvertMethodType
            except Exception: pass
            try: inp.meshConvertOperationType = adsk.fusion.MeshConvertOperationTypes.ParametricFeatureMeshConvertOperationType
            except Exception: pass
            feats.add(inp)
            ui.messageBox("Convertido a cuerpo solido. Ahora ve al espacio de trabajo Simulacion.")
        except Exception:
            ui.messageBox("No pude convertir automaticamente. Hazlo a mano: clic derecho en la malla > Convertir malla > Facetado.\n\n" + traceback.format_exc())
    except Exception:
        if ui: ui.messageBox("Error:\n" + traceback.format_exc())
