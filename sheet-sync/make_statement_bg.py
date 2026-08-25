#!/usr/bin/env python3
"""Synthesize the eclipse 'statement' background used by slides 2 (Mission)
and 13 (Vision) from scratch — no source-photo pixels, so no repair artifacts.
Color/geometry parameters measured from the original Canva export:
  bg horizontal gradient ~(14,14,17)->(23,23,27), disk r~368 @ (960,540),
  corona ring peak r~378 (bright upper-right, dim left), grain sigma~7.4.

Usage: make_statement_bg.py <label> <out.png>   # label: Mission | Vision
"""
import sys, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
FD = os.path.join(BASE, 'fonts')
W, H = 1920, 1080
CX, CY = 960.0, 540.0

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
r = np.sqrt((xx - CX) ** 2 + (yy - CY) ** 2)
th = np.arctan2(yy - CY, xx - CX)          # 0 = right, pi/2 = down

# --- background: horizontal gradient, slightly blue ---
t = xx / W
bg = np.dstack([14 + 9 * t, 14 + 9 * t, 17 + 10 * t])

# --- corona: sharp-edged ring + broad halo, angularly modulated ---
amp = 0.55 + 0.45 * np.cos(th + np.radians(25))       # max upper-right, min left
ring = np.exp(-np.clip(r - 378, 0, None) ** 2 / (2 * 55 ** 2)) * \
       np.exp(-np.clip(378 - r, 0, None) ** 2 / (2 * 12 ** 2))
halo = np.exp(-np.clip(r - 378, 0, None) / 230) * (r > 378)
glow_a = (ring * 1.0 + halo * 0.55) * amp
glow = np.dstack([glow_a * 46, glow_a * 41, glow_a * 86])

# --- moon disk: near-black with soft low-frequency mottle ---
rng = np.random.default_rng(20260826)
mottle = rng.normal(0, 1, (H // 90 + 2, W // 90 + 2))
mottle = np.kron(mottle, np.ones((90, 90)))[:H, :W]
import cv2  # noqa: E402
mottle = cv2.GaussianBlur(mottle.astype(np.float32), (0, 0), 40)
disk_col = np.dstack([12 + 3 * mottle, 12 + 3 * mottle, 18 + 3 * mottle])

edge = 1 / (1 + np.exp(-(r - 366) / 3.0))   # 0 inside disk, 1 outside
img = disk_col * (1 - edge)[..., None] + (bg + glow) * edge[..., None]

# faint chromosphere accents on the rim (tiny warm blips upper edge)
blip = np.exp(-((xx - 985) ** 2 + (yy - 168) ** 2) / (2 * 22 ** 2)) * 30
img[..., 0] += blip; img[..., 1] += blip * 0.85; img[..., 2] += blip * 0.7

# --- film grain (measured sigma ~7.4) ---
img += rng.normal(0, 7.4, img.shape)
img = np.clip(img, 0, 255).astype(np.uint8)
out = Image.fromarray(img)

# --- deck chrome ---
label = sys.argv[1] if len(sys.argv) > 1 else 'Mission'
path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(BASE, 'plates', 'slide-02.png')
d = ImageDraw.Draw(out)
F = lambda f, s: ImageFont.truetype(os.path.join(FD, f), s)
d.text((84, 68), label, font=F('archivo-3.ttf', 27), fill=(255, 255, 255))
logo = Image.open(os.path.join(BASE, '..', 'imxp-logo.png'))
lw = int(logo.width * (52 / logo.height))
logo_r = logo.resize((lw, 52), Image.LANCZOS)
out.paste(logo_r, (W - 84 - lw, 52), logo_r)
f = F('archivo-2.ttf', 24)
tw = d.textlength('Fundraise Deck', font=f)
d.text((W - 84 - tw, H - 52), 'Fundraise Deck', font=f, fill=(255, 255, 255))

out.save(path)
print('saved', path)
