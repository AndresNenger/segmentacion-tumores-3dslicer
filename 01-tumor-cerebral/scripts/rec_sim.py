import sys, os, time, subprocess, shutil
sys.path.append("C:/Users/Laboratorio/Downloads/femur_vh/deps_vid")
import imageio_ffmpeg

P = "C:/Users/Laboratorio/Downloads/tumor_cerebral"
OUT = P + "/segmento_simulador_EN.mp4"
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PROFILE = sys.argv[1]
FF = imageio_ffmpeg.get_ffmpeg_exe()


def ps(cmd):
    return subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, encoding="utf-8", errors="ignore").stdout.strip()


def title():
    return ps("(Get-Process msedge -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -ne '' }).MainWindowTitle")


if os.path.exists(PROFILE):
    shutil.rmtree(PROFILE, ignore_errors=True)
edge = subprocess.Popen([EDGE, "--kiosk", "http://localhost:8000/index.html#demo", "--edge-kiosk-type=fullscreen", "--no-first-run",
                         "--no-default-browser-check", "--user-data-dir=" + PROFILE, "--disable-features=Translate,msTranslate,msEdgeWelcomePage", "--lang=en-US", "--disable-translate"])
t0 = time.time()
proc = None
started = None
while time.time() - t0 < 240:
    t = title()
    if proc is None and "DEMO_RUNNING" in t:
        proc = subprocess.Popen([FF, "-y", "-hide_banner", "-loglevel", "error", "-f", "gdigrab", "-framerate", "30", "-draw_mouse", "0",
                                 "-i", "desktop", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", OUT], stdin=subprocess.PIPE)
        started = time.time()
        print("REC_START", round(started - t0, 1), flush=True)
    if proc is not None and "DEMO_DONE" in t:
        time.sleep(0.8)
        break
    time.sleep(0.4)
if proc is not None:
    proc.stdin.write(b"q"); proc.stdin.flush(); proc.wait(timeout=30)
    print("REC_STOP", round(time.time() - started, 1), flush=True)
else:
    print("NO_START, ultimo titulo:", title(), flush=True)
ps("Get-CimInstance Win32_Process -Filter \"Name='msedge.exe'\" | Where-Object { $_.CommandLine -like '*%s*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" % os.path.basename(PROFILE))
print("DONE", flush=True)
