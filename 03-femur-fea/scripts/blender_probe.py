import bpy, bmesh
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.wm.stl_import(filepath=r"C:\Users\Laboratorio\Downloads\femur_vh\femur_R_fusion_2.5mm.stl")
ob=bpy.context.selected_objects[0]; me=ob.data
bm=bmesh.new(); bm.from_mesh(me)
nm=[e for e in bm.edges if not e.is_manifold]; bd=[e for e in bm.edges if e.is_boundary]
print("PROBE verts",len(bm.verts),"tris",len(bm.faces),"no-manifold",len(nm),"borde",len(bd),"vol",round(bm.calc_volume()),flush=True)
# islas
seen=set(); isl=[]
for f in bm.faces:
    if f.index in seen: continue
    st=[f]; seen.add(f.index); n=0
    while st:
        c=st.pop(); n+=1
        for e in c.edges:
            for g in e.link_faces:
                if g.index not in seen: seen.add(g.index); st.append(g)
    isl.append(n)
print("PROBE islas",sorted(isl,reverse=True),flush=True)
dims=ob.dimensions; print("PROBE dims",[round(x,1) for x in dims])
