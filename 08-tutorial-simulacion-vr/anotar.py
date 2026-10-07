"""Genera las capturas anotadas del tutorial de la simulación VR.
Entradas: una captura del panel (ventana de 1400 x 1200) y fotogramas de la grabación del simulador (1920 x 1080).
Uso:  python anotar.py PANEL.png CARPETA_FRAMES CARPETA_SALIDA
"""
import sys, os
from PIL import Image, ImageDraw, ImageFont

panel_png, frames, out = sys.argv[1:4]
os.makedirs(out, exist_ok=True)
RED = (235, 40, 40)


def font(size):
    for n in ("segoeuib.ttf", "DejaVuSans-Bold.ttf", "arialbd.ttf"):
        for b in ("C:/Windows/Fonts/", "/usr/share/fonts/truetype/dejavu/", ""):
            try:
                return ImageFont.truetype(b + n, size)
            except Exception:
                pass
    return ImageFont.load_default()


def annotate(img, boxes, r=15, fs=24, w=5):
    img = img.convert("RGBA")
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    f = font(fs)
    for (x, y, bw, bh), label in boxes:
        d.rounded_rectangle([x - 5, y - 5, x + bw + 5, y + bh + 5], radius=8, outline=RED + (255,), width=w)
        cx, cy = x - 9, y - 9
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=RED + (255,), outline=(255, 255, 255, 255), width=3)
        tw = d.textlength(str(label), font=f)
        d.text((cx - tw / 2, cy - fs * 0.62), str(label), font=f, fill=(255, 255, 255, 255))
    return Image.alpha_composite(img, ov).convert("RGB")


# 1) panel general (1400 x 1200)
p = Image.open(panel_png).convert("RGB")
p = annotate(p, [((24, 173, 312, 48), 1), ((24, 236, 312, 284), 2), ((24, 534, 312, 320), 3), ((24, 871, 312, 92), 4), ((36, 1014, 215, 36), 5),
                 ((384, 26, 212, 18), 6)])
p.save(os.path.join(out, "01_panel_general.png"))

# 2) fotogramas de cada paso (se recorta la barra de subtítulos del video)
steps = {
    "02_paso1_ver": ("t6.png", 1),
    "03_paso2_ajustar": ("t13.png", 2),
    "04_paso3_marcar": ("t30.png", 3),
    "05_paso4_abrir": ("t38.png", 4),
    "06_paso5_resecar": ("t50.png", 5),
    "07_fisiologia": ("t59.png", 5),
}
for name, (fn, n) in steps.items():
    im = Image.open(os.path.join(frames, fn)).convert("RGB")
    im = im.crop((0, 0, 1920, 975))
    # botones de paso (n-ésimo), tarjeta de instrucciones y escena 3D
    xs = [30, 109, 188, 267, 346]
    boxes = [((xs[n - 1] - 2, 217, 76 if n < 5 else 76, 42), 1), ((30, 283, 390, 380), 2), ((470, 80, 1420, 860), 3)]
    if name == "07_fisiologia":
        boxes = [((30, 690, 390, 260), 1), ((480, 28, 285, 32), 2)]
    annotate(im, boxes, r=17, fs=26, w=6).resize((1600, int(975 * 1600 / 1920))).save(os.path.join(out, name + ".png"))
print("ok")
