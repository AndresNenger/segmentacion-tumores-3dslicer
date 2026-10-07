import sys, time, subprocess, json
sys.path.append("C:/Users/Laboratorio/Downloads/femur_vh/deps_vid")
import slicer, qt
import imageio_ffmpeg

P = "C:/Users/Laboratorio/Downloads/tumor_cerebral"
OUT = P + "/segmento_tarjetas_EN.mp4"
FPS = 24
st = json.load(open(P + "/estadisticas_segmentos.json"))
plan = json.load(open(P + "/plan_craneotomia.json"))


def gv(dct, key):
    for k, v in dct.items():
        if k.endswith("." + key):
            return v


T_, R_ = st["Tumor"], st["Referencia_sustancia_blanca_derecha"]
mw = slicer.util.mainWindow()
mw.showMaximized(); mw.raise_(); mw.activateWindow()


def pump(n=3):
    for _ in range(n):
        slicer.app.processEvents()


t0 = time.time()
while time.time() - t0 < 3:
    pump()
slicer.util.selectModule("Models")
pump(5)
title = mw.windowTitle
lbl = qt.QLabel(mw)
lbl.setAttribute(qt.Qt.WA_TransparentForMouseEvents)
lbl.setWordWrap(True)
lbl.setAlignment(qt.Qt.AlignLeft | qt.Qt.AlignVCenter)
lbl.setStyleSheet("background-color: #0d1117; color: #e8edf5; padding: 40px 90px;")


def card(step, title_txt, bullets, footer=""):
    li = "".join("<p style='margin:0 0 15px 0; font-size:27px; line-height:130%%'>&#9679;&nbsp; %s</p>" % b for b in bullets)
    lbl.setText(("<div style='font-size:20px; color:#f2c94c; font-weight:bold; margin-bottom:6px'>%s</div>"
                 "<div style='font-size:40px; font-weight:bold; margin-bottom:26px'>%s</div>%s"
                 "<div style='font-size:20px; color:#9fb3d1; margin-top:16px'>%s</div>") % (step, title_txt, li, footer))
    lbl.setGeometry(0, 0, mw.width, mw.height); lbl.show(); lbl.raise_(); pump(5)


card("RESULTS", "", [""])
ff = imageio_ffmpeg.get_ffmpeg_exe()
cmd = [ff, "-y", "-hide_banner", "-loglevel", "error", "-f", "gdigrab", "-framerate", str(FPS), "-draw_mouse", "0",
       "-i", "title=" + title, "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-preset", "veryfast",
       "-crf", "20", "-pix_fmt", "yuv420p", OUT]
proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
time.sleep(1.5)


def wait(sec):
    end = time.time() + sec
    while time.time() < end:
        pump(1); time.sleep(0.02)


try:
    card("RESULTS", "What the analysis shows", [
        "<b>Tumor volume:</b> %.1f cm³ · maximum diameter %.1f mm · roundness %.2f (almost spherical)." % (gv(T_, "volume_cm3"), gv(T_, "feret_diameter_mm"), gv(T_, "roundness")),
        "<b>Enhancement:</b> mean MRI intensity %.0f vs %.0f in white matter (≈ %.1f×); more heterogeneous (CV %.0f %% vs %.0f %%)." % (
            gv(T_, "mean"), gv(R_, "mean"), gv(T_, "mean") / gv(R_, "mean"), 100 * gv(T_, "stdev") / gv(T_, "mean"), 100 * gv(R_, "stdev") / gv(R_, "mean")),
        "<b>Location:</b> left frontal, next to the falx (midline), about %.0f mm below the scalp." % plan["profundidad_piel_superficie_tumor_mm"],
        "<b>Plan:</b> paramedian entry ≥ 15 mm from the midline · craniotomy window ≈ %d mm (tumor + 10 mm margin)." % plan["diametro_max_ventana_mm"],
        "<b>3D printing (Creality K1C, PLA):</b> template ≈ 1 h 45 min · scalp phantom ≈ 2 h 29 min · tumor model ≈ 41 min."], "")
    wait(17)
    card("LIMITATIONS & REGULATION", "Read before sharing", [
        "One public sample MRI (3D Slicer MRBrainTumor1); the segmentation was not validated against an expert ground truth.",
        "MRI intensities are signal units, not tissue properties: contrast enhancement is not a diagnosis (histology is needed).",
        "The template rests on a smoothed scalp surface; the scalp moves, so real guides need bone support and validation.",
        "<b>Not a medical device. Not for clinical use.</b> Real use needs a surgeon's plan, validation and regulatory approval (FDA, EU MDR, ARCSA)."], "")
    wait(17)
    card("BRAIN TUMOR · 3D SLICER + 3D PRINTING", "MRI → segmentation → tissue analysis → craniotomy template → 3D print", [
        "An academic exercise combining biomedical imaging and engineering.",
        "Data: 3D Slicer sample data (MRBrainTumor1) · Tools: 3D Slicer, Python, OrcaSlicer."], "")
    wait(7)
except Exception:
    import traceback
    print("ERROR", traceback.format_exc(), flush=True)
finally:
    try:
        proc.stdin.write(b"q"); proc.stdin.flush()
    except Exception:
        pass
    try:
        proc.wait(timeout=30)
    except Exception:
        proc.kill()
    print("REC_DONE", flush=True)
    slicer.app.quit()
