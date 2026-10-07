import slicer, numpy as np
from PIL import Image, ImageDraw
P = "C:/Users/Laboratorio/Downloads/tumor_cerebral"
for n in ("MRBrainTumor1", "MRBrainTumor2"):
    v = slicer.util.loadVolume(P + "/%s.nrrd" % n)
    a = slicer.util.arrayFromVolume(v).astype(np.float32)
    hi = np.percentile(a, 99.5)
    ks = list(range(20, a.shape[0] - 4, 6))
    tiles = []
    for k in ks:
        im = Image.fromarray((np.clip(a[k] / hi, 0, 1) * 255).astype(np.uint8)).resize((160, 160))
        ImageDraw.Draw(im).text((4, 4), "k=%d" % k, fill=255)
        tiles.append(im)
    cols = 8
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("L", (cols * 160, rows * 160))
    for t, im in enumerate(tiles):
        sheet.paste(im, ((t % cols) * 160, (t // cols) * 160))
    sheet.save(P + "/mosaico_%s.png" % n)
    print("OK", n, len(tiles), flush=True)
slicer.app.quit()
