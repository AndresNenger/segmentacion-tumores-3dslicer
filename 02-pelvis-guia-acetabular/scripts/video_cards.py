import sys, time, subprocess
sys.path.append("C:/Users/Laboratorio/Downloads/femur_vh/deps_vid")
import slicer, qt
import imageio_ffmpeg

P = "C:/Users/Laboratorio/Downloads/pelvis_guia"
OUT = P + "/segmento_tarjetas.mp4"
FPS = 24

mw = slicer.util.mainWindow()
mw.showMaximized()
mw.raise_()
mw.activateWindow()


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
    li = "".join("<p style='margin:0 0 16px 0; font-size:27px; line-height:130%%'>&#9679;&nbsp; %s</p>" % b for b in bullets)
    html = ("<div style='font-size:20px; color:#f2c94c; font-weight:bold; margin-bottom:6px'>%s</div>"
            "<div style='font-size:38px; font-weight:bold; margin-bottom:28px'>%s</div>%s"
            "<div style='font-size:20px; color:#9fb3d1; margin-top:18px'>%s</div>") % (step, title_txt, li, footer)
    lbl.setText(html)
    lbl.setGeometry(0, 0, mw.width, mw.height)
    lbl.show()
    lbl.raise_()
    pump(5)


card("PASO 10", "Protocolo de prueba física (propuesto)", [""], "")
ff = imageio_ffmpeg.get_ffmpeg_exe()
cmd = [ff, "-y", "-hide_banner", "-loglevel", "error", "-f", "gdigrab", "-framerate", str(FPS), "-draw_mouse", "0",
       "-i", "title=" + title, "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-preset", "veryfast",
       "-crf", "20", "-pix_fmt", "yuv420p", OUT]
proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
time.sleep(1.5)
if proc.poll() is not None:
    print("FFMPEG_FAIL", proc.stderr.read().decode(errors="ignore")[:500], flush=True)
    slicer.app.quit()
    sys.exit(1)
print("FFMPEG_OK", flush=True)


def wait(sec):
    end = time.time() + sec
    while time.time() < end:
        pump(1)
        time.sleep(0.02)


try:
    card("PASO 10", "Protocolo de prueba física (propuesto)", [
        "Imprimir la réplica ósea y la guía al 100 % (PLA o PETG, solo banco de pruebas).",
        "Medir con calibre: orificio Ø 9,2 mm, tubo Ø 16 mm y espesor de los parches.",
        "Asentar la guía sobre la réplica y medir la holgura con galgas (objetivo propuesto: ≤ 0,5 mm).",
        "Pasar una varilla Ø 4 mm por el tubo y medir el ángulo del eje (objetivo: 40° de inclinación y 15° de anteversión).",
        "Repetir al menos 5 veces y registrar la desviación media y máxima."],
        "Los criterios de aceptación deben definirse con el equipo clínico y de ingeniería.")
    wait(15)
    card("PASO 11 · MARCO REGULATORIO (1/2)", "Resumen orientativo", [
        "Investigación y banco de pruebas: sin pacientes, pero con aprobación institucional y, si se usan datos o muestras humanas, de un comité de ética.",
        "<b>Estados Unidos (FDA):</b> las guías quirúrgicas impresas en 3D suelen ser dispositivos de clase II (notificación 510(k)); la excepción para dispositivos a medida es muy restringida.",
        "<b>Unión Europea (MDR 2017/745):</b> «a medida» (Anexo XIII, prescripción escrita) frente a «ajustado al paciente» (producción en lote bajo responsabilidad del fabricante, con evaluación de conformidad completa).",
        "<b>Ecuador (ARCSA):</b> registro sanitario obligatorio para fabricar, importar o comercializar dispositivos médicos de uso humano (norma sustitutiva ARCSA-DE-2026-003-DASP, abril de 2026)."],
        "Fuentes: FDA, MDCG 2021-3, ARCSA. Resumen educativo, no es asesoría legal.")
    wait(22)
    card("PASO 11 · MARCO REGULATORIO (2/2)", "Qué se exige normalmente antes de usarla en pacientes", [
        "Sistema de gestión de calidad (ISO 13485) y gestión de riesgos (ISO 14971).",
        "Biocompatibilidad del material (serie ISO 10993) y esterilización validada (por ejemplo, vapor: ISO 17665).",
        "Validación del proceso de impresión y del software de planificación (IEC 62304).",
        "Verificación y validación del diseño: ensayos con modelos físicos y, según el caso, evidencia clínica.",
        "Trazabilidad, etiquetado y vigilancia posterior a la comercialización."],
        "Normas de referencia habituales. Consultar siempre a un especialista en asuntos regulatorios.")
    wait(16)
    card("RESUMEN", "Del CT a la guía quirúrgica académica", [
        "Segmentación del CT  →  análisis estructural  →  guía de la copa acetabular  →  preparación de impresión  →  prueba física  →  regulación.",
        "<b>Siguiente paso:</b> imprimir la réplica y la guía, medir el asiento y la desviación del eje.",
        "Ejercicio académico con datos de un cadáver (VSD · Fischer, Sci Data 2023 · CC BY-NC-SA). No es un dispositivo médico ni apto para uso clínico."],
        "")
    wait(11)
except Exception:
    import traceback
    print("ERROR", traceback.format_exc(), flush=True)
finally:
    try:
        proc.stdin.write(b"q")
        proc.stdin.flush()
    except Exception:
        pass
    try:
        proc.wait(timeout=30)
    except Exception:
        proc.kill()
    print("REC_DONE", flush=True)
    slicer.app.quit()
