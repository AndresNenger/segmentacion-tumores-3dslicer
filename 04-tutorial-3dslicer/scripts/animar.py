import sys, os, json, math, wave, subprocess
sys.path.append("C:/Users/Laboratorio/Downloads/femur_vh/deps_vid")
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import imageio_ffmpeg

B = "C:/Users/Laboratorio/Downloads/tutorial_segmentacion"
FF = imageio_ffmpeg.get_ffmpeg_exe()
W, H, FPS = 1920, 1080, 30
G = json.load(open(B + "/guion.json", encoding="utf-8"))
steps, extra = G["steps"], G["extra"]
BG = (11, 16, 20)
ACC = (58, 209, 192)
RED = (235, 40, 40)
F_T = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 46)
F_S = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 30)
F_N = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 26)
F_BIG = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 78)
F_MED = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 40)
FS = 30 if False else None


def dur(name):
    with wave.open(B + "/voz/%s.wav" % name) as w:
        return w.getnframes() / w.getframerate()


def wrap(d, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= maxw:
            cur = t
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def ease(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3 - 2 * u)


def grad_bg():
    a = np.zeros((H, W, 3), np.uint8)
    for y in range(H):
        t = y / H
        a[y, :, :] = (int(11 + 14 * t), int(16 + 18 * t), int(20 + 26 * t))
    return Image.fromarray(a)


BGIMG = grad_bg()

# ---------------------------------------------------------------- tarjetas
def card(title, sub, step_label=None):
    img = BGIMG.copy()
    d = ImageDraw.Draw(img)
    y = 330
    if step_label:
        d.text((140, y - 70), step_label, font=F_N, fill=ACC)
    for ln in wrap(d, title, F_BIG, W - 280):
        d.text((140, y), ln, font=F_BIG, fill=(255, 255, 255)); y += 92
    y += 20
    for ln in wrap(d, sub, F_MED, W - 280):
        d.text((140, y), ln, font=F_MED, fill=(190, 205, 220)); y += 56
    d.rectangle([140, 270, 300, 276], fill=ACC)
    return img


def thumbnail():
    base = Image.open(B + "/capturas/09_semillas_tumor_sin_marcas.png").convert("RGB")
    base = base.resize((1280, int(base.height * 1280 / base.width)))
    base = base.crop((0, 0, 1280, 720))
    sh = Image.new("RGB", (1280, 720), (8, 12, 16))
    sh.paste(base, (0, 0))
    ov = Image.new("RGBA", (1280, 720), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for x in range(0, 800):
        od.line([(x, 0), (x, 720)], fill=(8, 12, 16, int(235 * (1 - x / 800))))
    sh = Image.alpha_composite(sh.convert("RGBA"), ov).convert("RGB")
    d = ImageDraw.Draw(sh)
    f1 = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 92)
    f2 = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 40)
    y = 120
    for ln in ("Segmenta un", "tumor cerebral", "en 3D Slicer"):
        d.text((60, y), ln, font=f1, fill=(255, 255, 255)); y += 104
    d.rectangle([60, 70, 220, 78], fill=ACC)
    d.text((60, 560), "Tutorial paso a paso para principiantes", font=f2, fill=ACC)
    sh.save(B + "/miniatura_youtube.png")


# ---------------------------------------------------------------- escena de captura con marcas animadas
def scene_frames(step, secs, hold_in=0.9):
    """Genera los fotogramas de una captura: aparece, hace zoom suave a la zona marcada, se dibujan los recuadros y el clic."""
    src = Image.open(B + "/capturas/%s_sin_marcas.png" % step["name"]).convert("RGB")
    sw, sh_ = src.size
    items = step["items"]
    click = step["click"]
    # zona de interés = unión de recuadros
    if items:
        xs = [i["rect"][0] for i in items] + [i["rect"][0] + i["rect"][2] for i in items]
        ys = [i["rect"][1] for i in items] + [i["rect"][1] + i["rect"][3] for i in items]
        fx0, fy0, fx1, fy1 = min(xs), min(ys), max(xs), max(ys)
    else:
        fx0, fy0, fx1, fy1 = 0, 0, sw, sh_
    cx, cy = (fx0 + fx1) / 2, (fy0 + fy1) / 2
    area_top, area_h = 130, H - 130 - 150       # zona de imagen
    base_scale = min(W / sw, area_h / sh_)
    fw, fh = max(60, fx1 - fx0), max(60, fy1 - fy0)
    zoom_t = max(1.0, min(3.2, 0.82 * min(W / fw, area_h / fh) / base_scale))
    zoom_t = 1.0 + (zoom_t - 1.0) * 0.9
    n = int(secs * FPS)
    out = []
    for f in range(n):
        t = f / FPS
        z = 1.0 + (zoom_t - 1.0) * ease((t - 0.5) / 2.2)
        scale = base_scale * z
        vw, vh = sw * scale, sh_ * scale
        # centro de la vista: del centro de la imagen al centro de la zona de interés
        k = ease((t - 0.5) / 2.2)
        icx = (sw / 2) * (1 - k) + cx * k
        icy = (sh_ / 2) * (1 - k) + cy * k
        ox = W / 2 - icx * scale
        oy = area_top + area_h / 2 - icy * scale
        ox = min(0, max(W - vw, ox)) if vw > W else (W - vw) / 2
        oy = min(area_top, max(area_top + area_h - vh, oy)) if vh > area_h else area_top + (area_h - vh) / 2
        frame = BGIMG.copy()
        im = src.resize((max(1, int(vw)), max(1, int(vh))), Image.BILINEAR)
        # recorte a la zona visible
        crop_l, crop_t = int(max(0, -ox)), int(max(0, area_top - oy))
        paste = im.crop((crop_l, crop_t, min(im.width, crop_l + W), min(im.height, crop_t + area_h)))
        frame.paste(paste, (int(max(0, ox)), int(max(area_top, oy))))
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        # recuadros: aparecen escalonados
        for idx, it in enumerate(items):
            a = ease((t - (hold_in + 0.55 * idx)) / 0.5)
            if a <= 0:
                continue
            x, y, w_, h_ = it["rect"]
            X0, Y0 = ox + x * scale - 8, oy + y * scale - 8
            X1, Y1 = ox + (x + w_) * scale + 8, oy + (y + h_) * scale + 8
            col = RED + (int(255 * a),)
            d.rounded_rectangle([X0, Y0, X1, Y1], radius=10, outline=col, width=6)
            bx, by = X0 - 4, Y0 - 4
            d.ellipse([bx - 20, by - 20, bx + 20, by + 20], fill=col, outline=(255, 255, 255, int(255 * a)), width=3)
            lab = it["label"]
            tw = d.textlength(lab, font=F_N)
            d.text((bx - tw / 2, by - 17), lab, font=F_N, fill=(255, 255, 255, int(255 * a)))
        # clic: el cursor llega desde la esquina, se hace una onda
        if click:
            t_c = hold_in + 0.55 * max(0, len(items)) + 0.3
            ccx, ccy = ox + click[0] * scale, oy + click[1] * scale
            tt = (t - t_c)
            if tt > -1.0:
                u = ease((tt + 1.0) / 1.0)
                sx, sy = ccx + 260, ccy + 200
                px, py = sx + (ccx - sx) * u, sy + (ccy - sy) * u
                poly = [(0, 0), (0, 40), (11, 31), (18, 47), (26, 44), (19, 29), (33, 29)]
                d.polygon([(px + 6 + a_, py + 4 + b_) for a_, b_ in poly], fill=(255, 255, 255, 255), outline=(0, 0, 0, 255))
                if 0 <= tt < 1.2:
                    for r0, c0 in ((20, 0.0), (20, 0.3)):
                        rr = r0 + 90 * ease((tt - c0) / 0.9)
                        al = int(255 * (1 - ease((tt - c0) / 0.9)))
                        if tt - c0 > 0:
                            d.ellipse([ccx - rr, ccy - rr, ccx + rr, ccy + rr], outline=(255, 200, 0, al), width=6)
        frame = Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB")
        # cabecera y subtitulo
        d2 = ImageDraw.Draw(frame)
        d2.rectangle([0, 0, W, 112], fill=(8, 12, 16))
        d2.rectangle([0, 112, W, 116], fill=ACC)
        for ln in wrap(d2, step["title"], F_T, W - 140)[:1]:
            d2.text((70, 30), ln, font=F_T, fill=(255, 255, 255))
        out.append(frame)
    return out


def subtitle_overlay(frame, text, secs_frac=1.0):
    d = ImageDraw.Draw(frame, "RGBA")
    lines = wrap(d, text, F_S, W - 220)
    hh = 30 + 42 * len(lines)
    d.rectangle([0, H - hh - 20, W, H], fill=(0, 0, 0, 205))
    y = H - hh - 2
    for ln in lines:
        tw = d.textlength(ln, font=F_S)
        d.text(((W - tw) / 2, y), ln, font=F_S, fill=(255, 255, 255, 255)); y += 42
    return frame


def legend_overlay(frame, items):
    d = ImageDraw.Draw(frame, "RGBA")
    x = 70
    y = H - 255 if False else None
    return frame


# ---------------------------------------------------------------- ensamblado
segments = []   # (frames_list, wav_path)
thumbnail()
intro_d = dur("intro") + 0.8
segments.append(("intro", intro_d))
for s in steps:
    segments.append((s["name"], dur(s["name"]) + 1.2))
outro_d = dur("outro") + 1.0
segments.append(("outro", outro_d))

# pistas de audio: cada segmento tiene su wav y relleno de silencio
cmd = [FF, "-y", "-hide_banner", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H), "-r", str(FPS), "-i", "-",
       "-c:v", "libx264", "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", B + "/_video_mudo.mp4"]
pipe = subprocess.Popen(cmd, stdin=subprocess.PIPE)
timeline = []
t_acc = 0.0
nfr = 0


def push(img):
    global nfr
    pipe.stdin.write(np.asarray(img.convert("RGB")).tobytes())
    nfr += 1


by_name = {s["name"]: s for s in steps}
for name, d_ in segments:
    n = int(round(d_ * FPS))
    if name == "intro":
        base = card("Cómo segmentar un tumor cerebral con 3D Slicer", "Tutorial paso a paso para principiantes", "TUTORIAL")
        sm = "Ejercicio académico con datos de ejemplo · no es un diagnóstico"
        for f in range(n):
            im = base.copy()
            a = ease(f / (0.8 * FPS))
            if a < 1:
                im = Image.blend(BGIMG, im, a)
            d = ImageDraw.Draw(im)
            tw = d.textlength(sm, font=F_S)
            d.text((140, H - 140), sm, font=F_S, fill=(150, 165, 180))
            push(im)
        voz = "intro"
    elif name == "outro":
        base = card("Resumen", "Volumen del tumor: 16,9 cm³  ·  Herramientas: Paint, Grow from seeds, Smoothing, Islands, Segment Statistics", "LISTO")
        for f in range(n):
            im = base.copy()
            d = ImageDraw.Draw(im)
            sm = "Ejercicio académico con datos de ejemplo de 3D Slicer (MRBrainTumor1) · no es un diagnóstico ni sirve para decisiones médicas"
            for k, ln in enumerate(wrap(d, sm, F_S, W - 280)):
                d.text((140, H - 190 + 42 * k), ln, font=F_S, fill=(150, 165, 180))
            push(im)
        voz = "outro"
    else:
        st = by_name[name]
        frames = scene_frames(st, d_)
        for f, im in enumerate(frames):
            sub = st["voz"].replace("Em Ar Brain Tumor uno", "MRBrainTumor1").replace("tres de", "3D")
            push(subtitle_overlay(im, sub))
        voz = name
    timeline.append((voz, t_acc))
    t_acc += n / FPS

pipe.stdin.close()
pipe.wait()
print("FRAMES", nfr, "DUR", round(nfr / FPS, 1), flush=True)

# audio: concatenar los wav con su inicio exacto
inputs, filt, labels = [], [], []
for i, (voz, t0) in enumerate(timeline):
    inputs += ["-i", B + "/voz/%s.wav" % voz]
    filt.append("[%d:a]adelay=%d|%d[a%d]" % (i, int((t0 + 0.4) * 1000), int((t0 + 0.4) * 1000), i))
    labels.append("[a%d]" % i)
fg = ";".join(filt) + ";" + "".join(labels) + "amix=inputs=%d:normalize=0[aout]" % len(timeline)
open(B + "/_audio_graph.txt", "w").write(fg)
subprocess.run([FF, "-y", "-hide_banner", "-loglevel", "error"] + inputs + ["-filter_complex_script", B + "/_audio_graph.txt", "-map", "[aout]", "-c:a", "aac", "-b:a", "192k", B + "/_audio.m4a"], check=True)
subprocess.run([FF, "-y", "-hide_banner", "-loglevel", "error", "-i", B + "/_video_mudo.mp4", "-i", B + "/_audio.m4a", "-c:v", "copy", "-c:a", "copy", "-shortest",
                "-movflags", "+faststart", B + "/tutorial_segmentar_tumor_3DSlicer.mp4"], check=True)
json.dump(timeline, open(B + "/_timeline.json", "w"))
print("OK", flush=True)
