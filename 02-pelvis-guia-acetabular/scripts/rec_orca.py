import sys, os, time, subprocess, ctypes
sys.path.append("C:/Users/Laboratorio/Downloads/femur_vh/deps_vid")
import imageio_ffmpeg

P = "C:/Users/Laboratorio/Downloads/pelvis_guia"
ORCA = "C:/Program Files/OrcaSlicer/orca-slicer.exe"
MODE = sys.argv[1] if len(sys.argv) > 1 else "test"      # test | rec
SECS = float(sys.argv[2]) if len(sys.argv) > 2 else 14.0
FF = imageio_ffmpeg.get_ffmpeg_exe()
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()
user32 = ctypes.windll.user32


class RECT(ctypes.Structure):
    _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long), ("r", ctypes.c_long), ("b", ctypes.c_long)]


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def ps(cmd):
    return subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True).stdout.strip()


proc = subprocess.Popen([ORCA, P + "/placa_prueba_fisica.3mf"])
print("PID", proc.pid, flush=True)
hwnd = 0
t0 = time.time()
while time.time() - t0 < 60:
    out = ps("(Get-Process -Id %d -ErrorAction SilentlyContinue).MainWindowHandle" % proc.pid)
    if out and out != "0":
        hwnd = int(out)
        break
    time.sleep(1)
print("HWND", hwnd, ps("(Get-Process -Id %d).MainWindowTitle" % proc.pid), flush=True)
time.sleep(14)                       # carga de las piezas
user32.ShowWindow(hwnd, 3)           # maximizar
user32.SetForegroundWindow(hwnd)
time.sleep(4)
def key(vk):
    user32.keybd_event(vk, 0, 0, 0)
    time.sleep(0.05)
    user32.keybd_event(vk, 0, 2, 0)
    time.sleep(0.4)
user32.SetForegroundWindow(hwnd)
time.sleep(0.5)
time.sleep(2.5)
rc = RECT()
user32.GetClientRect(hwnd, ctypes.byref(rc))
pt = POINT(0, 0)
user32.ClientToScreen(hwnd, ctypes.byref(pt))
cw, ch = (rc.r - rc.l) // 2 * 2, (rc.b - rc.t) // 2 * 2
print("REGION", pt.x, pt.y, cw, ch, flush=True)
base = [FF, "-y", "-hide_banner", "-loglevel", "error", "-f", "gdigrab", "-framerate", "24", "-draw_mouse", "0",
        "-offset_x", str(pt.x), "-offset_y", str(pt.y), "-video_size", "%dx%d" % (cw, ch), "-i", "desktop"]
if MODE == "test":
    subprocess.run(base + ["-frames:v", "1", P + "/orca_test.png"])
    print("TEST_DONE", flush=True)
else:
    p = subprocess.Popen(base + ["-t", str(SECS), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                                  P + "/segmento_orca_raw.mp4"], stdin=subprocess.PIPE)
    p.wait()
    print("REC_DONE", flush=True)
subprocess.run(["taskkill", "/F", "/PID", str(proc.pid)], capture_output=True)
