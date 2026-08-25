#!/usr/bin/env python3
"""Content-editor renderer for text-forward slides of the IMXP deck.

Re-renders editable text zones of a slide on top of its pristine plate
(sheet-sync/plates/slide-NN.png), using content from the "IMXP Deck -
Content Editor" Google Sheet. Zones are cleared with either a flat fill or
synthesized grain (noise statistics sampled from neighbouring pixels) so the
patch is invisible, then re-typeset in the deck's fonts.

Editable slides + which sheet fields they consume are defined in ZONES.
Slides not listed here are static; slide 9 (roadmap) is handled by render_slide.py, slide 7 is the Iceland
recap (make_recap_slide.py), and slide 8 is the FIAB demo video slide.

Usage:
  render_content_slide.py <slide_no> <fields.json> <output.png>
  fields.json = {"headline": "...", "subheadline": "...", "body": "...", "stats": "..."}

Prints JSON: {"ok": bool, "error": str|null, "overflow": [zone names that clipped]}
"""
import sys, json, os
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
FD = os.path.join(BASE, 'fonts')
PLATES = os.path.join(BASE, 'plates')

WHITE = (255, 255, 255)
INK = (12, 12, 15)

# Zone spec keys:
#  box: (x0,y0,x1,y1) area cleared + typeset
#  fill: 'flat' | 'noise'  (noise samples grain stats from `sample` strip)
#  sample: (x0,y0,x1,y1) region whose pixels feed fill color / noise stats
#  field(s): sheet columns joined with blank line
#  font: (file, size); align: 'left'|'center'; color; leading: line-height mult
#  bullets: prefix wrapped lines from '- ' items with a dot
ZONES = {
    2: [
        dict(name='statement', box=(320, 330, 1600, 760), fill='none',
             sample=None, fields=['headline'], valign='middle',
             font=('archivo-3.ttf', 64), align='center', color=WHITE, leading=1.22),
    ],
    3: [
        dict(name='subheadline', box=(852, 300, 1880, 420), fill='flat',
             sample=(860, 940, 1860, 1010), fields=['subheadline'],
             font=('archivo-3.ttf', 40), align='left', color=WHITE, leading=1.15),
        dict(name='bullets', box=(852, 440, 1880, 860), fill='flat',
             sample=(860, 940, 1860, 1010), fields=['body'],
             font=('inter-1.ttf', 31), align='left', color=(228, 228, 230),
             leading=1.35, bullets=True, para_gap=0.9),
    ],
    4: [
        dict(name='headline', box=(84, 130, 1250, 270), fill='flat',
             sample=(300, 60, 900, 110), fields=['headline'],
             font=('archivo-3.ttf', 45), align='left', color=INK, leading=1.12),
        dict(name='body', box=(84, 860, 1250, 1010), fill='flat',
             sample=(300, 60, 900, 110), fields=['body'],
             font=('archivo-3.ttf', 33), align='left', color=INK, leading=1.15),
    ],
    13: [
        dict(name='statement', box=(170, 330, 1750, 770), fill='none',
             sample=None, fields=['headline', 'body'], valign='middle',
             font=('archivo-3.ttf', 52), align='center', color=WHITE,
             leading=1.25, para_gap=1.2),
    ],
    17: [
        dict(name='headline', box=(84, 170, 1180, 290), fill='inpaint',
             sample=None, fields=['headline'],
             font=('archivo-3.ttf', 40), align='left', color=WHITE, leading=1.15),
        dict(name='body', box=(84, 330, 1180, 760), fill='inpaint',
             sample=None, fields=['body'],
             font=('inter-1.ttf', 30), align='left', color=(232, 232, 232),
             leading=1.35, para_gap=0.9),
    ],
    18: [
        dict(name='headline', box=(84, 150, 810, 330), fill='inpaint', thresh=40, dilate=2,
             sample=None, fields=['headline'],
             font=('archivo-3.ttf', 58), align='left', color=WHITE, leading=1.1),
        dict(name='body', box=(105, 360, 810, 900), fill='inpaint', thresh=40, dilate=2,
             sample=None, fields=['body'],
             font=('inter-1.ttf', 28), align='left', color=(235, 235, 235),
             leading=1.32, para_gap=0.9),
    ],
}

EDITABLE = sorted(ZONES.keys())


def F(file, size):
    return ImageFont.truetype(os.path.join(FD, file), size)


def clear_zone(img, z):
    x0, y0, x1, y1 = z['box']
    a = np.asarray(img).astype(np.float32)
    if z['fill'] == 'none':
        return img
    if z['fill'] == 'flat':
        sx0, sy0, sx1, sy1 = z['sample']
        strip = a[sy0:sy1, sx0:sx1].reshape(-1, 3)
        mean = strip.mean(axis=0)
        a[y0:y1, x0:x1] = mean
        return Image.fromarray(a.astype(np.uint8))
    # 'inpaint': remove only the text pixels, preserving glow/grain backgrounds
    crop = a[y0:y1, x0:x1].astype(np.uint8)
    lum = crop.mean(axis=2)
    thresh = z.get('thresh', 90)
    mask = (lum > thresh).astype(np.uint8) * 255
    mask = cv2.dilate(mask, np.ones((5, 5), np.uint8), iterations=z.get('dilate', 1))
    filled = cv2.inpaint(crop, mask, 4, cv2.INPAINT_TELEA).astype(np.float32)
    # restore grain: measure high-frequency residual of untouched pixels
    blur = cv2.GaussianBlur(crop.astype(np.float32), (0, 0), 3)
    resid = (crop.astype(np.float32) - blur)[mask == 0]
    std = float(resid.std()) if resid.size else 0.0
    if std > 0.5:
        rng = np.random.default_rng(42)  # deterministic renders
        noise = rng.normal(0, std, filled.shape)
        m3 = (mask > 0)[..., None]
        filled = np.where(m3, filled + noise, filled)
    a[y0:y1, x0:x1] = np.clip(filled, 0, 255)
    return Image.fromarray(a.astype(np.uint8))


def wrap(d, text, font, maxw):
    lines = []
    for raw in text.split('\n'):
        raw = raw.rstrip()
        if not raw:
            lines.append('')
            continue
        words = raw.split(' ')
        cur = ''
        for w in words:
            t = (cur + ' ' + w).strip()
            if d.textlength(t, font=font) <= maxw or not cur:
                cur = t
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def typeset(img, z, text):
    """Draw text in the zone; auto-shrink font until it fits. Returns overflow bool."""
    d = ImageDraw.Draw(img)
    x0, y0, x1, y1 = z['box']
    file, size = z['font']
    bullets = z.get('bullets', False)
    if bullets:
        text = '\n'.join(('• ' + ln[2:] if ln.startswith('- ') else ln)
                         for ln in text.split('\n'))
    while size >= 16:
        font = F(file, size)
        lh = int(size * z.get('leading', 1.2))
        para_gap = int(size * z.get('para_gap', 0.6))
        lines = wrap(d, text, font, (x1 - x0))
        total = sum(para_gap if ln == '' else lh for ln in lines)
        if total <= (y1 - y0):
            break
        size -= 2
    y = y0
    if z.get('valign') == 'middle':
        y = y0 + max(0, ((y1 - y0) - total) // 2)
    for ln in lines:
        if ln == '':
            y += para_gap
            continue
        if z['align'] == 'center':
            tw = d.textlength(ln, font=font)
            x = x0 + ((x1 - x0) - tw) / 2
        else:
            x = x0
        d.text((x, y), ln, font=font, fill=z['color'])
        y += lh
    return total > (y1 - y0)


def render(slide_no, fields, out_path):
    plate = Image.open(os.path.join(PLATES, f'slide-{slide_no:02d}.png')).convert('RGB')
    overflow = []
    for z in ZONES[slide_no]:
        text = '\n\n'.join(fields.get(f, '').strip()
                           for f in z['fields'] if fields.get(f, '').strip())
        if not text:
            continue  # empty field -> leave original zone untouched
        plate = clear_zone(plate, z)
        if typeset(plate, z, text):
            overflow.append(z['name'])
    plate.save(out_path)
    return overflow


def main():
    slide_no = int(sys.argv[1])
    fields = json.load(open(sys.argv[2], encoding='utf-8'))
    out_path = sys.argv[3]
    res = {'ok': False, 'error': None, 'overflow': []}
    try:
        if slide_no not in ZONES:
            raise ValueError(f'slide {slide_no} is not an editable slide; editable: {EDITABLE}')
        res['overflow'] = render(slide_no, fields, out_path)
        res['ok'] = True
    except Exception as e:
        res['error'] = f'{type(e).__name__}: {e}'
    print(json.dumps(res))


if __name__ == '__main__':
    main()
