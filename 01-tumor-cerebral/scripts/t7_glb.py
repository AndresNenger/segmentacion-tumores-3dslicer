import bpy, os
P = r"C:\Users\Laboratorio\Downloads\tumor_cerebral"
bpy.ops.wm.read_factory_settings(use_empty=True)
parts = [  # archivo, nombre, color RGBA, proporcion de decimado
    ("piel.stl", "skin", (0.93, 0.76, 0.66, 0.35), 0.45),
    ("vr_craneo_aprox.stl", "skull", (0.92, 0.90, 0.82, 1.0), 0.30),
    ("vr_colgajo_oseo.stl", "bone_flap", (0.97, 0.94, 0.80, 1.0), 0.6),
    ("tumor_modelo.stl", "tumor", (1.0, 0.80, 0.10, 1.0), 0.5),
    ("plantilla_craneotomia.stl", "template", (0.10, 0.75, 0.70, 1.0), 0.30),
    ("contorno_craneotomia.stl", "outline", (1.0, 0.12, 0.12, 1.0), 1.0),
    ("trayectoria.stl", "trajectory", (1.0, 0.35, 0.10, 1.0), 1.0),
]
for fn, name, col, ratio in parts:
    bpy.ops.wm.stl_import(filepath=os.path.join(P, fn), global_scale=0.001)
    ob = bpy.context.selected_objects[0]
    ob.name = name
    ob.data.name = name
    if ratio < 1.0:
        m = ob.modifiers.new("dec", "DECIMATE"); m.ratio = ratio
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.modifier_apply(modifier="dec")
    bpy.ops.object.shade_smooth()
    mat = bpy.data.materials.new(name + "_mat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = col
    bsdf.inputs["Alpha"].default_value = col[3]
    bsdf.inputs["Roughness"].default_value = 0.55
    if col[3] < 1.0:
        try:
            mat.surface_render_method = "BLENDED"
        except Exception:
            mat.blend_method = "BLEND"
    ob.data.materials.append(mat)
    print("PART", name, len(ob.data.polygons), flush=True)
out = os.path.join(P, "vr_escena_tumor.glb")
bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", export_apply=True, export_yup=True)
print("GLB", out, round(os.path.getsize(out) / 1e6, 2), "MB", flush=True)
