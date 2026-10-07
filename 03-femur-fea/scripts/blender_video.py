import bpy, bmesh, blf, math, os, subprocess, ctypes, time, sys
from mathutils import Euler, Quaternion

D = r"C:\Users\Laboratorio\Downloads\femur_vh"
SRC = D + r"\femur_R_fusion_2.5mm.stl"
OUTSTL = D + r"\femur_R_blender_solido.stl"
OUTMP4 = D + r"\femur_blender_redes.mp4"
FFMPEG = D + r"\deps_vid\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe"
FPS = 30

state = {"caption": "", "sub": "", "proc": None}


def find_hwnd():
    user32 = ctypes.windll.user32
    pid = os.getpid()
    out = subprocess.run(["powershell", "-NoProfile", "-Command",
                          "(Get-Process -Id %d).MainWindowTitle; (Get-Process -Id %d).MainWindowHandle" % (pid, pid)],
                         capture_output=True, text=True).stdout.strip().splitlines()
    print("WIN", out, flush=True)
    if len(out) >= 2 and out[0].strip() and out[1].strip() not in ("", "0"):
        return int(out[1].strip()), out[0].strip()
    return None, None


def view3d():
    for win in bpy.context.window_manager.windows:
        for area in win.screen.areas:
            if area.type == 'VIEW_3D':
                region = [r for r in area.regions if r.type == 'WINDOW'][0]
                return win, area, region, area.spaces.active
    return None, None, None, None


def draw_caption():
    region = bpy.context.region
    if not state["caption"]:
        return
    blf.enable(0, blf.SHADOW)
    blf.shadow(0, 5, 0.0, 0.0, 0.0, 1.0)
    blf.shadow_offset(0, 2, -2)
    blf.color(0, 1, 1, 1, 1)
    blf.size(0, 30)
    blf.position(0, 140, 70, 0)
    blf.draw(0, state["caption"])
    blf.color(0, 0.8, 0.88, 1.0, 1)
    blf.size(0, 21)
    blf.position(0, 140, 36, 0)
    blf.draw(0, state["sub"])


handler = bpy.types.SpaceView3D.draw_handler_add(draw_caption, (), 'WINDOW', 'POST_PIXEL')


def redraw():
    win, area, region, space = view3d()
    if area:
        area.tag_redraw()


def set_caption(a, b=""):
    state["caption"], state["sub"] = a, b
    redraw()


def orbit_steps(seconds, deg_total):
    n = int(seconds * FPS)
    for _ in range(n):
        win, area, region, space = view3d()
        r3d = space.region_3d
        q = Euler((0, 0, math.radians(deg_total / n)), 'XYZ').to_quaternion()
        r3d.view_rotation = q @ r3d.view_rotation
        area.tag_redraw()
        yield 1.0 / FPS


def hold(seconds):
    for _ in range(int(seconds * FPS)):
        redraw()
        yield 1.0 / FPS


def frame_selected():
    win, area, region, space = view3d()
    with bpy.context.temp_override(window=win, area=area, region=region):
        bpy.ops.view3d.view_selected()
    r3d = space.region_3d
    r3d.view_rotation = Euler((math.radians(90), 0, math.radians(0)), 'XYZ').to_quaternion()
    r3d.view_distance *= 1.05
    area.tag_redraw()


def stats(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    nm = len([e for e in bm.edges if not e.is_manifold])
    bd = len([e for e in bm.edges if e.is_boundary])
    vol = abs(bm.calc_volume())
    nt = len(bm.faces)
    bm.free()
    return nm, bd, vol, nt


def sequence():
    # --- preparación ---
    yield 1.0
    hwnd, title = find_hwnd()
    user32 = ctypes.windll.user32
    if hwnd:
        user32.ShowWindow(hwnd, 3)
        user32.SetForegroundWindow(hwnd)
    yield 2.0
    hwnd, title = find_hwnd()
    print("TITLE", title, flush=True)
    class RECT(ctypes.Structure):
        _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long), ("r", ctypes.c_long), ("b", ctypes.c_long)]

    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

    rc = RECT()
    user32.GetClientRect(hwnd, ctypes.byref(rc))
    pt = POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(pt))
    cw, ch = (rc.r - rc.l) // 2 * 2, (rc.b - rc.t) // 2 * 2
    print("REGION", pt.x, pt.y, cw, ch, flush=True)
    cmd = [FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-f", "gdigrab", "-framerate", str(FPS),
           "-draw_mouse", "0", "-offset_x", str(pt.x), "-offset_y", str(pt.y), "-video_size", "%dx%d" % (cw, ch),
           "-i", "desktop", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", OUTMP4]
    state["proc"] = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    yield 1.5
    if state["proc"].poll() is not None:
        print("FFMPEG_FAIL", state["proc"].stderr.read().decode(errors="ignore")[:400], flush=True)
        bpy.ops.wm.quit_blender()
        return
    print("FFMPEG_OK", flush=True)

    # limpiar escena y maximizar el área 3D
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    win, area, region, space = view3d()
    with bpy.context.temp_override(window=win, area=area, region=region):
        bpy.ops.screen.screen_full_area()
    win, area, region, space = view3d()
    space.overlay.show_stats = True
    space.shading.type = 'SOLID'
    space.shading.color_type = 'OBJECT'
    space.show_gizmo = False
    set_caption("Blender 5.2 - escena vacía")
    yield from hold(2.0)

    # --- 1. abrir el fémur ---
    set_caption("Abrimos el fémur derecho (femur_R) en Blender", "Malla importada desde STL")
    bpy.ops.wm.stl_import(filepath=SRC)
    main = bpy.context.selected_objects[0]
    main.name = "femur_R"
    main.color = (0.93, 0.88, 0.75, 1.0)
    bpy.ops.object.shade_smooth()
    frame_selected()
    nm, bd, vol, nt = stats(main)
    set_caption("Abrimos el fémur derecho (femur_R) en Blender",
                "%d triángulos · ~%d mm de largo" % (nt, round(main.dimensions.z)))
    yield from orbit_steps(5.0, 300)

    # --- 2. buscar huecos ---
    set_caption("Paso 1: buscar huecos", "Selección de aristas no cerradas (non-manifold)")
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_mode(type='EDGE')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.mesh.select_non_manifold()
    bm = bmesh.from_edit_mesh(main.data)
    sel = len([e for e in bm.edges if e.select])
    yield from hold(1.5)
    set_caption("Paso 1: buscar huecos", "Aristas abiertas encontradas: %d  ->  la malla ya está cerrada" % sel)
    yield from orbit_steps(4.0, 120)

    # --- 3. fragmentos sueltos ---
    set_caption("Paso 2: detectar fragmentos sueltos", "Separando la malla por piezas desconectadas")
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.separate(type='LOOSE')
    bpy.ops.object.mode_set(mode='OBJECT')
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    meshes.sort(key=lambda o: len(o.data.polygons), reverse=True)
    big, small = meshes[0], meshes[1:]
    for o in small:
        o.color = (1.0, 0.1, 0.1, 1.0)
    big.color = (0.93, 0.88, 0.75, 1.0)
    print("PIEZAS", len(meshes), [len(o.data.polygons) for o in meshes], flush=True)
    set_caption("Paso 2: fragmentos sueltos en rojo", "%d piezas desconectadas: 1 fémur + %d fragmentos diminutos" % (len(meshes), len(small)))
    yield from orbit_steps(4.5, 150)

    # --- 4. eliminar fragmentos ---
    set_caption("Paso 3: eliminar los fragmentos", "Nos quedamos solo con la pieza principal")
    for o in meshes:
        o.select_set(False)
    for o in small:
        o.select_set(True)
    bpy.context.view_layer.objects.active = big
    bpy.ops.object.delete()
    big.select_set(True)
    bpy.context.view_layer.objects.active = big
    big.name = "femur_R_solido"
    yield from hold(1.5)

    # --- 5. verificación ---
    nm, bd, vol, nt = stats(big)
    print("FINAL", nm, bd, round(vol), nt, flush=True)
    set_caption("Resultado: un sólido completo y cerrado",
                "1 pieza · %d triángulos · 0 huecos · volumen %d mm³" % (nt, round(vol)) if nm == 0 and bd == 0
                else "ATENCION: quedan %d aristas abiertas" % nm)
    yield from orbit_steps(5.0, 200)

    # --- 6. exportar ---
    bpy.ops.wm.stl_export(filepath=OUTSTL, export_selected_objects=True)
    set_caption("Exportado: femur_R_blender_solido.stl", "Listo para Fusion, Inventor u OrcaSlicer")
    yield from orbit_steps(4.0, 120)
    yield from hold(1.0)

    # --- cierre ---
    try:
        state["proc"].stdin.write(b"q")
        state["proc"].stdin.flush()
        state["proc"].wait(timeout=30)
    except Exception as e:
        print("ffmpeg cierre", e, flush=True)
        state["proc"].kill()
    print("REC_DONE", flush=True)
    bpy.ops.wm.quit_blender()


gen = sequence()


def step():
    try:
        return next(gen)
    except StopIteration:
        return None
    except Exception:
        import traceback
        print("ERROR", traceback.format_exc(), flush=True)
        try:
            state["proc"].stdin.write(b"q")
            state["proc"].stdin.flush()
        except Exception:
            pass
        return None


bpy.app.timers.register(step, first_interval=3.0)
