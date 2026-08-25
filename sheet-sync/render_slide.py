#!/usr/bin/env python3
"""Sheet-driven renderer for slide 7 (Platform Build Roadmap) of the IMXP deck.

Parses the raw text/CSV export of the 'IMXP Product Dev GANTT' Google Sheet,
matches each task row to a pill defined in label_map.json by EXACT task text,
computes every pill's timeline position from the sheet's live Start/End dates,
and renders slide-07.png in the deck's existing visual style.

Tasks present in the sheet that are neither mapped nor explicitly excluded
are NOT guessed at — they're reported so a human can add a label.

Input file format (canonical, produced from the live sheet by the sync task):
  one task per line, pipe-delimited, category repeated on every line:
    CATEGORY|TASK|STATUS|D-Mon-YY|D-Mon-YY|NOTES
  e.g.  Capture|Iceland: DBs + ingest tools|Started|20-Aug-26|1-Sep-26|
  Lines starting with '#' and blank lines are ignored.

Usage:
  render_slide.py <canonical_tasks_file> <label_map.json> <imxp-logo.png> <output.png>

Prints a JSON summary to stdout: {"unmapped": [...], "ok": bool, "error": str|null}
"""
import sys, json, os
from datetime import date
from PIL import Image, ImageDraw, ImageFont

FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts')
CATEGORIES = {'Capture', 'Build', 'Prove', 'Gates', 'Harvest', 'Field'}
MONTHS = {m: i + 1 for i, m in enumerate(
    ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'])}


def parse_date(s):
    d, mon, yy = s.strip().split('-')
    return date(2000 + int(yy), MONTHS[mon.capitalize()[:3]], int(d))


def parse_sheet(text):
    tasks = []
    for ln, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        parts = line.split('|')
        if len(parts) < 5:
            raise ValueError(f'line {ln}: expected CATEGORY|TASK|STATUS|START|END|NOTES, got: {line!r}')
        cat, task, status, start, end = (p.strip() for p in parts[:5])
        if cat not in CATEGORIES:
            raise ValueError(f'line {ln}: unknown category {cat!r}')
        tasks.append({
            'category': cat,
            'task': task,
            'status': status,
            'start': parse_date(start),
            'end': parse_date(end),
            'notes': parts[5].strip() if len(parts) > 5 else '',
        })
    return tasks


def main():
    raw_path, label_map_path, logo_path, out_path = sys.argv[1:5]
    summary = {'unmapped': [], 'ok': False, 'error': None}
    try:
        text = open(raw_path, encoding='utf-8').read()
        label_map = json.load(open(label_map_path))
        tasks = parse_sheet(text)
        by_task = {t['task']: t for t in tasks}

        excluded = set(label_map.get('excludedTasks', []))
        mapped_task_names = set()
        for g in label_map['groups'].values():
            mapped_task_names.update(g['tasks'])
        for anc in label_map['provingEvents'].values():
            mapped_task_names.add(anc['anchorTask'])
        mapped_task_names.update(label_map['gates'].keys())

        for t in tasks:
            if t['task'] not in mapped_task_names and t['task'] not in excluded:
                summary['unmapped'].append({
                    'category': t['category'], 'task': t['task'],
                    'start': t['start'].isoformat(), 'end': t['end'].isoformat(),
                })

        EPOCH = date(2026, 8, 1)
        END = date(2027, 8, 31)
        total_days = (END - EPOCH).days

        def mpos(d):
            return max(0.0, min(13.0, (d - EPOCH).days / total_days * 13.0))

        # resolve each group's live span from its member tasks (min start, max end)
        resolved = {}
        for gid, g in label_map['groups'].items():
            rows = [by_task[tn] for tn in g['tasks'] if tn in by_task]
            if not rows:
                continue
            resolved[gid] = {
                **g,
                'm0': mpos(min(r['start'] for r in rows)),
                'm1': mpos(max(r['end'] for r in rows)),
            }

        gates = []
        for task_name, g in label_map['gates'].items():
            if task_name in by_task:
                gates.append({**g, 'm': mpos(by_task[task_name]['start']),
                              'date_label': by_task[task_name]['start'].strftime('%b %-d').upper()})

        events = {}
        for name, anc in label_map['provingEvents'].items():
            t = by_task.get(anc['anchorTask'])
            if t:
                events[name] = mpos(t['end'])

        render(resolved, gates, events, logo_path, out_path)
        summary['ok'] = True
    except Exception as e:
        summary['error'] = f'{type(e).__name__}: {e}'
    print(json.dumps(summary))


def render(groups, gates, events, logo_path, out_path):
    W, H = 1920, 1080
    img = Image.new('RGB', (W, H), (11, 11, 14))
    d = ImageDraw.Draw(img)

    def F(file, size):
        return ImageFont.truetype(f'{FD}/{file}', size)

    NAVY1, NAVY2, NAVY3, NAVY4 = '#211d54', '#37337a', '#4d4a9e', '#7a77c9'
    TEAL, GREEN, YELLOW, LAV, ORANGE = '#8fe6e2', '#96eda1', '#ffd75e', '#c3bdf2', '#ffbe7d'
    INK, GRAY, LINE = '#ffffff', '#9aa0ae', '#2a2a34'
    PILL_INK = '#0c0c0f'

    d.text((84, 62), 'Product', font=F('archivo-3.ttf', 30), fill=INK)
    logo = Image.open(logo_path)
    lw = int(logo.width * (52 / logo.height))
    logo_r = logo.resize((lw, 52), Image.LANCZOS)
    img.paste(logo_r, (W - 84 - lw, 52), logo_r)

    hf = F('archivo-3.ttf', 62)
    d.text((84, 140), 'Our operating system ships alongside', font=hf, fill=INK)
    d.text((84, 216), 'the events that prove it', font=hf, fill=INK)
    d.text((84, 305), 'PLATFORM BUILD ROADMAP  ·  AUG 2026 – AUG 2027', font=F('inter-2.ttf', 22), fill=GRAY)

    X0, X1 = 470, 1836
    def mx(m):
        return X0 + (m / 13.0) * (X1 - X0)

    BY0, BY1, notch = 360, 418, 22
    segs = [(0, 3, "AUG – OCT '26", NAVY1), (3, 6, "NOV '26 – FEB '27", NAVY2),
            (6, 10, "MAR – JUN '27", NAVY3), (10, 13, "JUL – AUG '27", NAVY4)]
    for i, (m0, m1, label, col) in enumerate(segs):
        xa, xb = mx(m0), mx(m1)
        poly = [(xa, BY0), (xb, BY0), (xb + notch, (BY0 + BY1) / 2), (xb, BY1), (xa, BY1)]
        if i:
            poly.append((xa + notch, (BY0 + BY1) / 2))
        d.polygon(poly, fill=col)
        f = F('archivo-3.ttf', 30)
        tw = d.textlength(label, font=f)
        d.text(((xa + xb) / 2 - tw / 2 + notch / 2, (BY0 + BY1) / 2 - 18), label, font=f, fill='white')
    d.text((84, 374), 'Build Calendar', font=F('archivo-2.ttf', 27), fill=INK)

    def pill(x0, x1, y, h, col, label, fsize=21):
        f = F('inter-2.ttf', fsize)
        tw = d.textlength(label, font=f)
        needed = tw + 32
        if x1 - x0 < needed:
            x1 = x0 + needed
        if x1 > X1 + notch:
            x0 -= x1 - (X1 + notch)
            x1 = X1 + notch
        d.rounded_rectangle([x0, y, x1, y + h], radius=h / 2, fill=col)
        d.text(((x0 + x1) / 2 - tw / 2, y + h / 2 - fsize * 0.62), label, font=f, fill=PILL_INK)
        return x1

    def lane_label(text, y, sub=None):
        d.text((84, y), text, font=F('archivo-2.ttf', 26), fill=INK)
        if sub:
            d.text((84, y + 32), sub, font=F('inter-1.ttf', 17), fill=GRAY)

    for m in (3, 6, 10):
        d.line([(mx(m), 440), (mx(m), 828)], fill=LINE, width=2)

    PH = 40
    lane_label('Proving Events', 452)
    default_evt = {'ATOMIKA': 3.0, 'COHERENCE': 7.0, 'MIDNIGHT SUN': 10.6, 'EGYPT': 12.5}
    merged = {**default_evt, **events}
    f = F('archivo-2.ttf', 22)
    placed = []
    for name in sorted(merged, key=lambda n: merged[n]):
        tw = d.textlength(name, font=f)
        cx = mx(merged[name])
        half = tw / 2 + 18
        if placed and cx - half < placed[-1] + 14:
            cx = placed[-1] + 14 + half
        cx = min(cx, X1 + notch - half)
        d.rounded_rectangle([cx - half, 446, cx + half, 446 + PH], radius=PH / 2, fill=TEAL)
        d.text((cx - tw / 2, 446 + PH / 2 - 14), name, font=f, fill=PILL_INK)
        placed.append(cx + half)
    d.line([(X0 - 10, 510), (X1 + notch, 510)], fill=LINE, width=2)

    LANE_Y = {'Capture': (528,), 'Build': (588, 636), 'Prove': (736, 784), 'Harvest': (842,)}
    LANE_COL = {'Capture': GREEN, 'Build': YELLOW, 'Prove': LAV, 'Harvest': ORANGE}
    LANE_FSIZE = {'Capture': 21, 'Build': 21, 'Prove': 21, 'Harvest': 19}
    for lane, ys in [('Capture', (532,)), ('Build', (604,)), ('Harvest', (846,))]:
        sub = {'Capture': 'event data pipelines', 'Build': 'platform tooling', 'Harvest': 'templates for the next event'}[lane]
        lane_label(lane, ys[0], sub)
    lane_label('Prove', 752, 'festival-in-a-box')
    d.text((84, 694), 'Gates', font=F('archivo-2.ttf', 26), fill=INK)

    from collections import defaultdict
    rows = defaultdict(list)
    for g in groups.values():
        rows[(g['lane'], g.get('row', 0))].append(dict(g))
    for (lane, row), gs in rows.items():
        gs.sort(key=lambda g: g['m0'])
        prev_end = None
        y = LANE_Y[lane][row]
        prev_x1 = None
        for g in gs:
            x0, x1 = mx(g['m0']), mx(g['m1'])
            if prev_x1 is not None and x0 < prev_x1 + 10:
                x0 = prev_x1 + 10
            x1 = max(x1, x0 + 30)
            prev_x1 = pill(x0, x1, y, PH, LANE_COL[lane], g['label'], fsize=LANE_FSIZE[lane])

    gy = 706
    for g in gates:
        cx, s = mx(g['m']), 11
        d.polygon([(cx, gy - s), (cx + s, gy), (cx, gy + s), (cx - s, gy)], outline='#e04b3a', width=4)
        f = F('inter-2.ttf', 17)
        label = f"{g['date_label']} · {g['label']}"
        if g['side'] == 'left':
            tw = d.textlength(label, font=f)
            d.text((cx - 18 - tw, gy - 11), label, font=f, fill='#c23a2b')
        else:
            d.text((cx + 18, gy - 11), label, font=f, fill='#c23a2b')

    P0, P1 = 912, 1030
    d.rounded_rectangle([84, P0, W - 84, P1], radius=10, fill='#14181f', outline='#2a3140', width=2)
    d.text((116, P0 + 22), 'IMXP OPERATING SYSTEM', font=F('archivo-3.ttf', 26), fill='white')
    d.text((116, P0 + 62), 'Every event is a live test; each harvest feeds the next build.',
           font=F('inter-1.ttf', 20), fill='#9aa4b2')
    stages = [('DATA INGEST + STRUCTURE', "SEP – OCT '26"), ('PLAN + NEW SOLUTIONS', "OCT – DEC '26"),
              ('ATOMIKA · FIAB BETA', "NOV '26"), ('COHERENCE · FIAB RELEASE', "MAR '27")]
    sx = 820
    sw = (W - 84 - 20 - sx) / 4
    for i, (t, dt) in enumerate(stages):
        x = sx + i * sw
        d.line([(x, P0 + 24), (x, P1 - 24)], fill='#2a3140', width=2)
        d.text((x + 16, P0 + 32), t, font=F('inter-2.ttf', 15), fill='#7fe3e0')
        d.text((x + 16, P0 + 60), dt, font=F('inter-1.ttf', 16), fill='#9aa4b2')

    f = F('archivo-2.ttf', 24)
    tw = d.textlength('Fundraise Deck', font=f)
    d.text((W - 84 - tw, H - 44), 'Fundraise Deck', font=f, fill=INK)

    img.save(out_path)


if __name__ == '__main__':
    main()
