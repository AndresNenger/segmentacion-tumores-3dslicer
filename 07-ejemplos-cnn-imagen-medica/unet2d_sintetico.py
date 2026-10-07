"""U-Net 2D mínima para segmentar "lesiones" en imágenes sintéticas.

Sirve para entender el flujo de una CNN de segmentación sin descargar datos médicos:
1. se generan imágenes con un fondo ruidoso y manchas redondas (la "lesión"),
2. se entrena una U-Net pequeña,
3. se mide el coeficiente de Dice en imágenes que la red no vio.

No es un modelo médico: las imágenes son sintéticas. Para datos reales mira MONAI o nnU-Net (README).

Uso:  python unet2d_sintetico.py            (CPU, unos 20 segundos)
Requiere: torch, numpy.
"""
import time
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

torch.manual_seed(0)
np.random.seed(0)
DEV = "cuda" if torch.cuda.is_available() else "cpu"
N = 64


def make_sample():
    """Imagen N x N con ruido de fondo suave y 1-2 manchas más brillantes; devuelve (imagen, máscara)."""
    yy, xx = np.mgrid[0:N, 0:N]
    img = 0.25 + 0.15 * np.random.rand(N, N)
    # fondo suave tipo "tejido"
    img += 0.10 * np.sin(xx / 7.0 + np.random.rand() * 6) * np.cos(yy / 9.0 + np.random.rand() * 6)
    mask = np.zeros((N, N), np.float32)
    for _ in range(np.random.randint(1, 3)):
        cx, cy, r = np.random.randint(14, N - 14), np.random.randint(14, N - 14), np.random.randint(5, 10)
        blob = ((xx - cx) ** 2 + (yy - cy) ** 2) < r * r
        img[blob] += 0.30 + 0.1 * np.random.rand()
        mask[blob] = 1.0
    img += 0.05 * np.random.randn(N, N)
    return img.astype(np.float32), mask


def make_set(n):
    xs, ys = zip(*[make_sample() for _ in range(n)])
    return torch.tensor(np.stack(xs))[:, None], torch.tensor(np.stack(ys))[:, None]


def block(i, o):
    return nn.Sequential(nn.Conv2d(i, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU(inplace=True),
                         nn.Conv2d(o, o, 3, padding=1), nn.BatchNorm2d(o), nn.ReLU(inplace=True))


class UNet(nn.Module):
    def __init__(self, c=16):
        super().__init__()
        self.e1, self.e2, self.e3 = block(1, c), block(c, 2 * c), block(2 * c, 4 * c)
        self.up2, self.d2 = nn.ConvTranspose2d(4 * c, 2 * c, 2, stride=2), block(4 * c, 2 * c)
        self.up1, self.d1 = nn.ConvTranspose2d(2 * c, c, 2, stride=2), block(2 * c, c)
        self.out = nn.Conv2d(c, 1, 1)

    def forward(self, x):
        a = self.e1(x)                                  # N
        b = self.e2(F.max_pool2d(a, 2))                 # N/2
        c = self.e3(F.max_pool2d(b, 2))                 # N/4
        d = self.d2(torch.cat([self.up2(c), b], 1))     # N/2 (conexión de salto)
        d = self.d1(torch.cat([self.up1(d), a], 1))     # N
        return self.out(d)


def dice(logits, y, eps=1e-6):
    p = (torch.sigmoid(logits) > 0.5).float()
    inter = (p * y).sum((1, 2, 3))
    return ((2 * inter + eps) / (p.sum((1, 2, 3)) + y.sum((1, 2, 3)) + eps)).mean().item()


def dice_loss(logits, y, eps=1.0):
    p = torch.sigmoid(logits)
    inter = (p * y).sum((1, 2, 3))
    return 1 - ((2 * inter + eps) / (p.sum((1, 2, 3)) + y.sum((1, 2, 3)) + eps)).mean()


if __name__ == "__main__":
    xtr, ytr = make_set(600)
    xva, yva = make_set(100)
    net = UNet().to(DEV)
    opt = torch.optim.Adam(net.parameters(), 2e-3)
    bce = nn.BCEWithLogitsLoss()
    t0 = time.time()
    print("dispositivo:", DEV, "| parámetros:", sum(p.numel() for p in net.parameters()))
    for ep in range(1, 11):
        net.train()
        perm = torch.randperm(len(xtr))
        for i in range(0, len(xtr), 32):
            idx = perm[i:i + 32]
            x, y = xtr[idx].to(DEV), ytr[idx].to(DEV)
            opt.zero_grad()
            out = net(x)
            loss = bce(out, y) + dice_loss(out, y)
            loss.backward()
            opt.step()
        net.eval()
        with torch.no_grad():
            d = dice(net(xva.to(DEV)), yva.to(DEV))
        print("época %2d | pérdida %.3f | Dice validación %.3f | %.0f s" % (ep, loss.item(), d, time.time() - t0), flush=True)
    print("Dice final en imágenes no vistas: %.3f" % d)
