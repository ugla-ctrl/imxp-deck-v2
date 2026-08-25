#!/usr/bin/env python3
"""Generate slide 7: Iceland Eclipse 2026 recap.

Dark deck style: white imxp logo top-right, eyebrow top-left, big headline,
stat row, org roster, with the Hellissandur aerial photo as the right panel
(cropped from the Eclipse Trilogy Iceland slide). All figures come from the
deck itself (slides 5-6): combined revenue, participants, countries, artists.
"""
import os
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
FD = os.path.join(BASE, 'fonts')
W, H = 1920, 1080
INK = (12, 12, 15)
WHITE = (255, 255, 255)
DIM = (176, 178, 188)
TEAL = (143, 230, 226)


def F(file, size):
    return ImageFont.truetype(os.path.join(FD, file), size)


img = Image.new('RGB', (W, H), (8, 8, 10))
d = ImageDraw.Draw(img)

# right panel: aerial photo cropped from the Iceland trilogy slide plate
aerial_src = Image.open(os.path.join(BASE, '..', 'slides', 'slide-20.png')).convert('RGB')
panel_w = 700
# crop inside the photo half, excluding its baked-in logo (top) and footer (bottom)
crop = aerial_src.crop((893, 130, 1920, 1012))
scale = H / crop.height
crop = crop.resize((int(crop.width * scale), H), Image.LANCZOS)
img.paste(crop.crop((crop.width - panel_w, 0, crop.width, H)), (W - panel_w, 0))
# deck-style dark gradients over the photo so header/footer text reads cleanly
grad = Image.new('L', (1, 300), 0)
for gy in range(300):
    grad.putpixel((0, gy), int(200 * (1 - gy / 300)))
top_g = grad.resize((panel_w, 300))
img.paste(Image.new('RGB', (panel_w, 300), (8, 8, 10)), (W - panel_w, 0), top_g)
bot_g = top_g.transpose(Image.FLIP_TOP_BOTTOM).resize((panel_w, 200))
img.paste(Image.new('RGB', (panel_w, 200), (8, 8, 10)), (W - panel_w, H - 200), bot_g)
# soft blend edge into the dark ground
edge = Image.new('L', (160, H), 0)
ed = ImageDraw.Draw(edge)
for x in range(160):
    ed.line([(x, 0), (x, H)], fill=int(255 * (1 - x / 160)))
dark = Image.new('RGB', (160, H), (8, 8, 10))
img.paste(dark, (W - panel_w, 0), edge)

# header
d.text((84, 62), 'Events · Recap', font=F('archivo-3.ttf', 30), fill=WHITE)
logo = Image.open(os.path.join(BASE, '..', 'imxp-logo.png'))
lw = int(logo.width * (52 / logo.height))
logo_r = logo.resize((lw, 52), Image.LANCZOS)
img.paste(logo_r, (W - 84 - lw, 52), logo_r)

# headline
d.text((84, 170), 'Iceland Eclipse 2026:', font=F('archivo-3.ttf', 64), fill=WHITE)
d.text((84, 250), 'delivered', font=F('archivo-3.ttf', 64), fill=TEAL)
d.text((84, 356), 'SNÆFELLSNES PENINSULA · 11–15 AUGUST 2026 · SOLD OUT',
       font=F('inter-2.ttf', 22), fill=DIM)

# stat rows
stats = [
    ('$4.19M', 'combined revenue · Eclipse Festival + The Portal'),
    ('2,600', 'participants at the edge of the world'),
    ('60+', 'countries represented'),
    ('287', 'artists & speakers'),
]
y = 452
for num, label in stats:
    d.text((84, y), num, font=F('archivo-4.ttf', 54), fill=WHITE)
    d.text((360, y + 18), label, font=F('inter-1.ttf', 26), fill=DIM)
    y += 92

# portal + orgs
d.line([(84, y + 6), (1120, y + 6)], fill=(48, 48, 56), width=2)
d.text((84, y + 34), 'THE PORTAL', font=F('archivo-2.ttf', 26), fill=TEAL)
d.text((84, y + 74), 'Month-long immersive village and field lab · 109 confirmed participants',
       font=F('inter-1.ttf', 24), fill=DIM)
d.text((84, y + 128), 'With United Nations, NASA, OpenAI, MAPS, Playing for Change & many more',
       font=F('inter-2.ttf', 24), fill=WHITE)

# footer
f = F('archivo-2.ttf', 24)
tw = d.textlength('Fundraise Deck', font=f)
d.text((W - 84 - tw, H - 44), 'Fundraise Deck', font=f, fill=WHITE)

out = os.path.join(BASE, '..', 'slides', 'slide-07.png')
img.save(out)
print('saved', out)
