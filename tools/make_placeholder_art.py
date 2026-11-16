#!/usr/bin/env python3
"""Generate the placeholder pixel art, assets/assets.json and ART_GUIDE.md.

Every asset the app draws is defined in SPECS below (id, size, frames, description).
The app only ever reads assets/assets.json, so the final art can be dropped in by
replacing the PNGs (same size), or by editing assets.json (e.g. a different frame count).

Run:  python3 tools/make_placeholder_art.py          (needs Pillow)
      python3 tools/make_placeholder_art.py --keep    (only (re)writes assets.json + ART_GUIDE.md,
                                                       never overwrites existing PNGs)
"""
import json, math, os, random, sys
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'assets')
KEEP = '--keep' in sys.argv

# ---------------------------------------------------------------- palette (32 warm, earthy colours)
P = {
    'ink': '#2b1d16', 'dkbrown': '#4a3426', 'brown': '#6b4a32', 'ltbrown': '#8f6a48', 'tan': '#b8916a', 'sand': '#d9bf8f',
    'parch': '#ecdcb3', 'cream': '#f6ecd2', 'terra_dk': '#7a3223', 'terra': '#a84a2f', 'terra_lt': '#c96f47', 'ochre': '#c9962f',
    'gold': '#e0b84a', 'olive_dk': '#3c4a24', 'olive': '#5d6b34', 'sage': '#8a9455', 'leaf': '#b0b57a', 'stone_dk': '#5a5550',
    'stone': '#8a847a', 'stone_lt': '#b5ad9e', 'marble': '#ddd6c8', 'sea_dk': '#23394a', 'sea': '#3e5f73', 'sea_lt': '#6f8f9c',
    'sky': '#a9bfc4', 'wine': '#5e2333', 'purple': '#5a3a5e', 'white': '#f8f4ea', 'black': '#140e0b', 'skin': '#c98f62',
    'skin_dk': '#9c6440', 'red': '#8e2b22',
}
def C(name, a=255):
    h = P[name].lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)
CLEAR = (0, 0, 0, 0)

def img(w, h, bg=CLEAR): return Image.new('RGBA', (w, h), bg)
def rect(d, x0, y0, x1, y1, col):
    x0, x1 = sorted((x0, x1)); y0, y1 = sorted((y0, y1))
    d.rectangle([x0, y0, x1, y1], fill=C(col) if isinstance(col, str) else col)
def px(d, x, y, col): d.point((x, y), fill=C(col) if isinstance(col, str) else col)
def disc(d, cx, cy, r, col):
    for y in range(-r, r + 1):
        for x in range(-r, r + 1):
            if x * x + y * y <= r * r + r * 0.6: px(d, cx + x, cy + y, col)
def outline(im, col='ink'):
    """1px dark outline around opaque pixels (classic sprite look)"""
    w, h = im.size; src = im.load(); out = im.copy(); o = out.load()
    for y in range(h):
        for x in range(w):
            if src[x, y][3] == 0:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h and src[nx, ny][3] > 0:
                        o[x, y] = C(col); break
    return out
def noise_tile(w, h, base, specks, seed, density=0.12):
    r = random.Random(seed); im = img(w, h, C(base)); d = ImageDraw.Draw(im)
    for _ in range(int(w * h * density)):
        px(d, r.randrange(w), r.randrange(h), r.choice(specks))
    return im

# ---------------------------------------------------------------- sprite painters
def hero_sheet(layer):
    """6 columns (idle0, idle1, walk0-3) x 4 rows (down, up, left, right); 16x24 frames."""
    W, H = 16, 24
    sheet = img(W * 6, H * 4)
    for row, facing in enumerate(['down', 'up', 'left', 'right']):
        for col in range(6):
            f = img(W, H); d = ImageDraw.Draw(f)
            walk = col >= 2
            ph = (col - 2) % 4 if walk else 0
            bob = 1 if (not walk and col == 1) or (walk and ph in (1, 3)) else 0
            leg = [0, 1, 0, -1][ph] if walk else 0
            y0 = 2 + bob
            if layer == 'base':
                # legs + sandals
                rect(d, 6, 18 + bob, 7, 21 - max(0, leg), 'skin'); rect(d, 9, 18 + bob, 10, 21 - max(0, -leg), 'skin')
                rect(d, 5, 22 - max(0, leg), 7, 22 - max(0, leg), 'dkbrown'); rect(d, 9, 22 - max(0, -leg), 11, 22 - max(0, -leg), 'dkbrown')
                # tunic
                rect(d, 4, y0 + 8, 11, y0 + 16, 'cream'); rect(d, 4, y0 + 15, 11, y0 + 16, 'sand')
                rect(d, 4, y0 + 12, 11, y0 + 12, 'ltbrown')  # belt
                px(d, 7, y0 + 9, 'terra'); px(d, 8, y0 + 9, 'terra')  # clavus stripe hint
                # arms
                sw = [0, 1, 0, -1][ph] if walk else 0
                rect(d, 3, y0 + 9 + max(0, sw), 3, y0 + 13 + max(0, sw), 'skin'); rect(d, 12, y0 + 9 + max(0, -sw), 12, y0 + 13 + max(0, -sw), 'skin')
                # head
                rect(d, 5, y0 + 1, 10, y0 + 7, 'skin')
                rect(d, 5, y0, 10, y0 + 2, 'dkbrown')  # hair
                if facing == 'down':
                    px(d, 6, y0 + 4, 'ink'); px(d, 9, y0 + 4, 'ink'); px(d, 7, y0 + 6, 'skin_dk'); px(d, 8, y0 + 6, 'skin_dk')
                elif facing == 'up':
                    rect(d, 5, y0, 10, y0 + 5, 'dkbrown')
                elif facing == 'left':
                    px(d, 6, y0 + 4, 'ink'); rect(d, 9, y0, 10, y0 + 5, 'dkbrown')
                else:
                    px(d, 9, y0 + 4, 'ink'); rect(d, 5, y0, 6, y0 + 5, 'dkbrown')
            elif layer == 'toga':
                rect(d, 4, y0 + 8, 11, y0 + 17, 'white'); rect(d, 4, y0 + 8, 5, y0 + 17, 'marble')
                for i in range(6): px(d, 5 + i, y0 + 9 + i, 'marble')
                rect(d, 4, y0 + 17, 11, y0 + 17, 'stone_lt')
                if facing != 'up': rect(d, 10, y0 + 9, 11, y0 + 11, 'purple')
            elif layer == 'cloak':
                rect(d, 3, y0 + 8, 12, y0 + 15, 'terra_dk'); rect(d, 3, y0 + 8, 12, y0 + 8, 'terra')
                if facing == 'down': rect(d, 6, y0 + 8, 9, y0 + 9, 'gold')
            elif layer == 'laurel':
                for x in range(4, 12): px(d, x, y0 + 1 + (1 if x in (4, 11) else 0), 'olive')
                for x in (4, 6, 8, 10): px(d, x, y0, 'sage')
                px(d, 11, y0 + 2, 'olive_dk'); px(d, 4, y0 + 2, 'olive_dk')
            elif layer == 'satchel':
                rect(d, 11, y0 + 11, 13, y0 + 14, 'ltbrown'); px(d, 12, y0 + 11, 'gold')
                for i in range(4): px(d, 7 + i, y0 + 8 + i, 'dkbrown')
            f = outline(f) if layer == 'base' else f
            sheet.paste(f, (col * W, row * H), f)
    return sheet

def tile_via():
    im = img(16, 16, C('stone')); d = ImageDraw.Draw(im)
    stones = [(0, 0, 6, 4), (7, 0, 15, 5), (0, 5, 4, 10), (5, 6, 11, 10), (12, 6, 15, 11), (0, 11, 7, 15), (8, 11, 15, 15)]
    for x0, y0, x1, y1 in stones:
        rect(d, x0, y0, x1, y1, 'stone_lt'); rect(d, x0, y1, x1, y1, 'stone_dk'); rect(d, x1, y0, x1, y1, 'stone_dk')
        px(d, x0 + 1, y0 + 1, 'marble')
    return im

def bg_tile(theme):
    seeds = {'provinciae': ('parch', ['sand', 'tan', 'cream']), 'villa': ('sage', ['olive', 'leaf', 'olive_dk']),
             'hortus': ('olive', ['leaf', 'sage', 'olive_dk', 'terra_lt']), 'via': ('leaf', ['sage', 'sand', 'olive']),
             'taberna': ('sand', ['tan', 'stone_lt', 'ltbrown']), 'rus': ('leaf', ['sage', 'ochre', 'olive']),
             'silva': ('olive_dk', ['olive', 'dkbrown', 'sage']), 'castra': ('tan', ['ltbrown', 'sand', 'brown']),
             'templa': ('marble', ['stone_lt', 'cream', 'stone']), 'ludus': ('stone_lt', ['stone', 'marble', 'sand']),
             'mare': ('sea', ['sea_lt', 'sea_dk', 'sky']), 'urbs': ('stone', ['stone_dk', 'stone_lt', 'tan']),
             'creta': ('ochre', ['tan', 'sand', 'terra_lt']), 'caelum': ('sky', ['white', 'sea_lt', 'marble']),
             'triclinium': ('terra_dk', ['terra', 'wine', 'ochre']), 'theatrum': ('sand', ['ochre', 'tan', 'terra_lt']),
             'forum': ('marble', ['stone_lt', 'gold', 'stone'])}
    base, specks = seeds[theme]
    im = noise_tile(32, 32, base, specks, hash(theme) % 999, 0.10)
    d = ImageDraw.Draw(im)
    if theme in ('taberna', 'urbs', 'forum', 'templa', 'ludus', 'triclinium'):  # paving / floor grid
        line = {'triclinium': 'wine', 'forum': 'stone_lt', 'templa': 'stone_lt'}.get(theme, 'stone_dk')
        for i in range(0, 32, 8): rect(d, 0, i, 31, i, line); rect(d, i + (4 if (i // 8) % 2 else 0), 0, i + (4 if (i // 8) % 2 else 0), 31, line)
        if theme == 'triclinium':
            for x, y in ((4, 4), (20, 4), (12, 20), (28, 20)): rect(d, x, y, x + 2, y + 2, 'ochre')
    if theme == 'mare':
        for y in (6, 18, 28):
            for x in range(0, 32, 8): px(d, x + 2, y, 'sea_lt'); px(d, x + 3, y - 1, 'sea_lt'); px(d, x + 4, y, 'sea_lt')
    if theme == 'caelum':
        disc(d, 10, 12, 4, 'white'); disc(d, 15, 11, 5, 'white'); disc(d, 20, 13, 3, 'white')
    if theme == 'rus':
        for y in range(2, 32, 6): rect(d, 0, y, 31, y, 'ochre')
    return im

def prop(name):
    if name == 'cypress':
        im = img(12, 28); d = ImageDraw.Draw(im)
        for y in range(2, 25):
            hw = int(1 + 4 * math.sin(math.pi * (y - 1) / 25))
            rect(d, 6 - hw, y, 5 + hw, y, 'olive_dk')
            if y % 3 == 0: px(d, 6 - hw + 1, y, 'olive')
        rect(d, 5, 25, 6, 27, 'dkbrown'); return outline(im)
    if name == 'pine':  # umbrella pine
        im = img(24, 24); d = ImageDraw.Draw(im)
        rect(d, 11, 10, 12, 23, 'dkbrown'); px(d, 10, 14, 'dkbrown'); px(d, 13, 12, 'dkbrown')
        for x in range(2, 22):
            top = 4 + int(abs(x - 12) / 3); rect(d, x, top, x, 10 - (1 if x in (2, 21) else 0), 'olive_dk')
        for x in range(5, 19, 3): px(d, x, 5, 'olive')
        return outline(im)
    if name == 'olive':
        im = img(18, 18); d = ImageDraw.Draw(im)
        rect(d, 8, 9, 9, 17, 'brown'); disc(d, 9, 7, 6, 'sage'); disc(d, 6, 6, 3, 'leaf'); px(d, 11, 5, 'olive'); px(d, 7, 9, 'olive')
        return outline(im)
    if name == 'bush':
        im = img(12, 9); d = ImageDraw.Draw(im); disc(d, 4, 5, 3, 'olive'); disc(d, 8, 5, 3, 'olive'); px(d, 4, 3, 'leaf'); px(d, 8, 4, 'terra_lt')
        return outline(im)
    if name == 'column':
        im = img(8, 24); d = ImageDraw.Draw(im)
        rect(d, 0, 0, 7, 2, 'marble'); rect(d, 1, 3, 6, 21, 'marble'); rect(d, 2, 3, 2, 21, 'stone_lt'); rect(d, 5, 3, 5, 21, 'stone_lt'); rect(d, 0, 22, 7, 23, 'stone_lt')
        return outline(im)
    if name == 'statue':
        im = img(10, 22); d = ImageDraw.Draw(im)
        rect(d, 1, 16, 8, 21, 'stone_lt'); rect(d, 3, 6, 6, 15, 'marble'); rect(d, 4, 2, 5, 5, 'marble'); rect(d, 7, 6, 7, 9, 'marble')
        return outline(im)
    if name == 'house':
        im = img(28, 22); d = ImageDraw.Draw(im)
        rect(d, 2, 9, 25, 21, 'cream'); rect(d, 2, 18, 25, 21, 'sand')
        for i in range(8): rect(d, 1 + i, 8 - i, 26 - i, 8 - i, 'terra' if i % 2 else 'terra_lt')
        rect(d, 12, 14, 15, 21, 'dkbrown'); rect(d, 5, 12, 7, 14, 'dkbrown'); rect(d, 20, 12, 22, 14, 'dkbrown')
        return outline(im)
    if name == 'shop':
        im = img(28, 22); d = ImageDraw.Draw(im)
        rect(d, 1, 6, 26, 21, 'sand'); rect(d, 4, 11, 23, 21, 'dkbrown')
        for x in range(1, 27): px(d, x, 6, 'terra' if (x // 3) % 2 else 'cream'); px(d, x, 7, 'terra' if (x // 3) % 2 else 'cream')
        for x in (6, 10, 14, 18): px(d, x, 14, 'gold'); px(d, x + 1, 16, 'terra_lt')
        rect(d, 3, 19, 24, 20, 'ltbrown')
        return outline(im)
    if name == 'sheep':
        im = img(12, 9); d = ImageDraw.Draw(im)
        disc(d, 6, 4, 3, 'white'); rect(d, 2, 3, 10, 6, 'white'); rect(d, 9, 2, 11, 4, 'ink'); px(d, 3, 7, 'ink'); px(d, 8, 7, 'ink')
        return outline(im)
    if name == 'rock':
        im = img(12, 8); d = ImageDraw.Draw(im); disc(d, 6, 5, 3, 'stone'); rect(d, 3, 5, 9, 7, 'stone'); px(d, 5, 3, 'stone_lt')
        return outline(im)
    if name == 'vine':
        im = img(10, 16); d = ImageDraw.Draw(im)
        rect(d, 4, 4, 5, 15, 'brown'); rect(d, 0, 4, 9, 4, 'ltbrown')
        for x, y in ((2, 6), (7, 7), (3, 10), (6, 11)): disc(d, x, y, 1, 'olive')
        px(d, 7, 9, 'wine'); px(d, 2, 8, 'wine'); px(d, 6, 13, 'wine')
        return outline(im)
    if name == 'wheat':
        im = img(12, 12); d = ImageDraw.Draw(im)
        for x in range(1, 12, 2):
            rect(d, x, 3, x, 11, 'ochre'); px(d, x, 2, 'gold'); px(d, x, 3, 'gold')
        return im
    if name == 'boat':
        im = img(28, 20); d = ImageDraw.Draw(im)
        for i in range(5): rect(d, 3 + i, 14 + i, 24 - i, 14 + i, 'brown' if i < 2 else 'dkbrown')
        rect(d, 13, 2, 13, 14, 'dkbrown'); rect(d, 7, 3, 19, 11, 'cream'); rect(d, 7, 7, 19, 7, 'terra')
        rect(d, 1, 13, 4, 13, 'brown'); rect(d, 23, 12, 26, 13, 'brown')
        return outline(im)
    if name == 'wave':
        im = img(14, 6); d = ImageDraw.Draw(im)
        for x in range(14): px(d, x, 3 + int(round(math.sin(x / 2.2) * 1.5)), 'sea_lt')
        px(d, 4, 1, 'white'); px(d, 11, 1, 'white')
        return im
    if name == 'tent':
        im = img(20, 16); d = ImageDraw.Draw(im)
        for i in range(10): rect(d, 9 - i, 5 + i, 10 + i, 5 + i, 'sand' if i % 3 else 'tan')
        rect(d, 9, 9, 10, 15, 'dkbrown'); rect(d, 9, 2, 10, 5, 'brown'); px(d, 11, 2, 'red'); px(d, 12, 3, 'red')
        return outline(im)
    if name == 'standard':
        im = img(10, 24); d = ImageDraw.Draw(im)
        rect(d, 4, 4, 5, 23, 'brown'); rect(d, 1, 3, 8, 4, 'gold'); disc(d, 4, 2, 2, 'gold'); rect(d, 2, 7, 7, 12, 'red'); px(d, 4, 9, 'gold')
        return outline(im)
    if name == 'amphora':
        im = img(8, 14); d = ImageDraw.Draw(im)
        rect(d, 3, 0, 4, 2, 'terra'); disc(d, 3, 7, 3, 'terra'); rect(d, 3, 10, 4, 13, 'terra'); px(d, 2, 5, 'terra_lt'); rect(d, 1, 2, 1, 4, 'terra_dk'); rect(d, 6, 2, 6, 4, 'terra_dk')
        return outline(im)
    if name == 'bench':
        im = img(18, 10); d = ImageDraw.Draw(im)
        rect(d, 0, 3, 17, 4, 'ltbrown'); rect(d, 1, 5, 2, 9, 'brown'); rect(d, 15, 5, 16, 9, 'brown'); rect(d, 6, 0, 10, 2, 'cream')  # tablet on bench
        return outline(im)
    if name == 'templum':
        im = img(32, 28); d = ImageDraw.Draw(im)
        for i in range(8): rect(d, 15 - i * 2, 1 + i, 16 + i * 2, 1 + i, 'marble')
        rect(d, 2, 9, 29, 10, 'stone_lt')
        for x in (4, 10, 16, 22, 27): rect(d, x, 11, x + 1, 23, 'marble')
        rect(d, 1, 24, 30, 27, 'stone_lt'); rect(d, 2, 24, 29, 24, 'marble')
        return outline(im)
    if name == 'wall':
        im = img(24, 14); d = ImageDraw.Draw(im)
        rect(d, 0, 3, 23, 13, 'stone');
        for x in range(0, 24, 6): rect(d, x, 0, x + 3, 3, 'stone')
        for y in (6, 9, 12): rect(d, 0, y, 23, y, 'stone_dk')
        return outline(im)
    if name == 'labyrinth':
        im = img(24, 24); d = ImageDraw.Draw(im)
        for r_ in (11, 8, 5, 2):
            d.rectangle([12 - r_, 12 - r_, 11 + r_, 11 + r_], outline=C('terra_dk'))
        rect(d, 11, 0, 12, 4, CLEAR); rect(d, 19, 11, 23, 12, CLEAR); rect(d, 11, 19, 12, 23, CLEAR)
        return im
    if name == 'cloud':
        im = img(24, 10); d = ImageDraw.Draw(im); disc(d, 7, 6, 3, 'white'); disc(d, 12, 4, 4, 'white'); disc(d, 17, 6, 3, 'white'); rect(d, 4, 6, 20, 9, 'white')
        return im
    if name == 'feather':
        im = img(10, 10); d = ImageDraw.Draw(im)
        for i in range(8): px(d, 1 + i, 8 - i, 'stone_dk'); px(d, 2 + i, 8 - i, 'white'); px(d, 1 + i, 7 - i, 'white')
        return im
    if name == 'couch':  # triclinium lectus
        im = img(24, 12); d = ImageDraw.Draw(im)
        rect(d, 0, 4, 23, 8, 'wine'); rect(d, 0, 2, 3, 8, 'wine'); rect(d, 0, 9, 23, 9, 'brown'); rect(d, 2, 10, 3, 11, 'brown'); rect(d, 20, 10, 21, 11, 'brown')
        rect(d, 4, 3, 22, 3, 'gold')
        return outline(im)
    if name == 'lamp':
        im = img(8, 20); d = ImageDraw.Draw(im)
        rect(d, 3, 6, 4, 19, 'dkbrown'); rect(d, 1, 19, 6, 19, 'dkbrown'); rect(d, 1, 4, 6, 5, 'ochre'); px(d, 3, 2, 'gold'); px(d, 3, 3, 'terra_lt'); px(d, 4, 1, 'gold')
        return outline(im)
    if name == 'mask':  # theatre mask
        im = img(12, 12); d = ImageDraw.Draw(im)
        disc(d, 6, 6, 5, 'cream'); px(d, 4, 5, 'ink'); px(d, 8, 5, 'ink'); rect(d, 4, 8, 8, 8, 'ink'); px(d, 3, 7, 'ink'); px(d, 9, 7, 'ink')
        return outline(im)
    if name == 'arena':
        im = img(32, 16); d = ImageDraw.Draw(im)
        d.ellipse([0, 2, 31, 15], fill=C('tan')); d.ellipse([5, 5, 26, 12], fill=C('sand'))
        for x in range(2, 30, 4): px(d, x, 4, 'ltbrown')
        return outline(im)
    raise ValueError(name)

def landmark(name):
    if name == 'milestone':
        im = img(10, 18); d = ImageDraw.Draw(im)
        rect(d, 1, 3, 8, 16, 'stone_lt'); rect(d, 2, 1, 7, 2, 'stone_lt'); rect(d, 0, 16, 9, 17, 'stone'); rect(d, 7, 3, 8, 16, 'stone')
        return outline(im)
    if name == 'fountain':
        im = img(24, 20); d = ImageDraw.Draw(im)
        d.ellipse([1, 10, 22, 19], fill=C('stone_lt')); d.ellipse([3, 11, 20, 17], fill=C('sea_lt'))
        rect(d, 10, 3, 13, 13, 'stone_lt'); rect(d, 8, 2, 15, 3, 'marble'); px(d, 11, 0, 'sky'); px(d, 12, 1, 'sky'); px(d, 9, 5, 'sky'); px(d, 14, 6, 'sky')
        return outline(im)
    if name == 'shrine':
        im = img(20, 24); d = ImageDraw.Draw(im)
        for i in range(5): rect(d, 9 - i * 2, 2 + i, 10 + i * 2, 2 + i, 'terra')
        rect(d, 2, 7, 3, 19, 'marble'); rect(d, 16, 7, 17, 19, 'marble'); rect(d, 4, 8, 15, 19, 'dkbrown'); rect(d, 8, 12, 11, 17, 'gold')
        rect(d, 1, 20, 18, 23, 'stone_lt')
        return outline(im)
    if name == 'arch':
        im = img(48, 40); d = ImageDraw.Draw(im)
        rect(d, 2, 6, 45, 39, 'marble'); rect(d, 0, 2, 47, 8, 'stone_lt'); rect(d, 4, 0, 43, 2, 'marble')
        d.ellipse([14, 14, 33, 33], fill=CLEAR); rect(d, 14, 24, 33, 39, CLEAR)
        for x in (5, 9, 38, 42): rect(d, x, 12, x + 1, 37, 'stone_lt')
        rect(d, 16, 3, 31, 6, 'gold')
        return outline(im)
    if name == 'capitolium':
        im = img(96, 72); d = ImageDraw.Draw(im)
        for i in range(10): rect(d, 6 + i * 2, 62 - i * 0, 89 - i * 2, 62, 'stone_lt')
        for k in range(6): rect(d, 6 + k * 3, 60 + k, 89 - k * 3, 60 + k, 'marble' if k % 2 else 'stone_lt')
        rect(d, 10, 26, 85, 30, 'marble')
        for i in range(16): rect(d, 48 - i * 3, 8 + i, 47 + i * 3, 8 + i, 'marble' if i < 14 else 'stone_lt')
        rect(d, 36, 14, 59, 20, 'gold')
        for x in range(13, 84, 10): rect(d, x, 31, x + 3, 58, 'marble'); rect(d, x + 3, 31, x + 3, 58, 'stone_lt')
        rect(d, 10, 58, 85, 59, 'stone_lt'); px(d, 48, 6, 'gold'); px(d, 47, 7, 'gold'); px(d, 49, 7, 'gold')
        return outline(im)
    raise ValueError(name)

def waypoint(kind):
    im = img(12, 12); d = ImageDraw.Draw(im)
    if kind == 'locked':
        disc(d, 5, 6, 4, 'stone_dk'); disc(d, 5, 5, 3, 'stone')
    elif kind == 'current':
        disc(d, 5, 6, 5, 'gold'); disc(d, 5, 5, 3, 'cream'); px(d, 5, 5, 'gold')
    elif kind == 'done':
        disc(d, 5, 6, 4, 'terra_dk'); disc(d, 5, 5, 3, 'terra'); px(d, 4, 4, 'terra_lt'); px(d, 5, 5, 'gold')
    elif kind == 'rest':
        disc(d, 5, 6, 4, 'sea_dk'); disc(d, 5, 5, 3, 'sea_lt')
    return outline(im) if kind != 'current' else im

def coin(kind):
    col = {'as': ('terra_dk', 'terra_lt'), 'dupondius': ('ochre', 'gold'), 'sestertius': ('ltbrown', 'ochre'),
           'denarius': ('stone', 'marble'), 'aureus': ('ochre', 'gold'), 'quinarius': ('stone_dk', 'stone_lt')}[kind]
    im = img(12, 12); d = ImageDraw.Draw(im)
    disc(d, 5, 5, 5, col[0]); disc(d, 5, 5, 4, col[1]); rect(d, 4, 3, 6, 7, col[0]); px(d, 3, 3, 'white')
    return im

def icon(kind):
    im = img(16, 16); d = ImageDraw.Draw(im)
    if kind == 'tunic': rect(d, 4, 3, 11, 13, 'cream'); rect(d, 2, 3, 13, 5, 'cream'); rect(d, 4, 8, 11, 8, 'ltbrown'); rect(d, 7, 3, 8, 13, 'terra')
    if kind == 'toga': rect(d, 3, 2, 12, 14, 'white'); rect(d, 3, 2, 4, 14, 'purple'); [px(d, 5 + i, 3 + i, 'marble') for i in range(8)]
    if kind == 'cloak': rect(d, 3, 2, 12, 13, 'terra_dk'); rect(d, 3, 2, 12, 3, 'terra'); rect(d, 6, 3, 9, 4, 'gold')
    if kind == 'laurel':
        for i in range(7): px(d, 3 + i // 2, 12 - i, 'olive'); px(d, 12 - i // 2, 12 - i, 'olive'); px(d, 2 + i // 2, 11 - i, 'sage'); px(d, 13 - i // 2, 11 - i, 'sage')
    if kind == 'satchel': rect(d, 3, 6, 12, 13, 'ltbrown'); rect(d, 3, 6, 12, 8, 'brown'); px(d, 7, 8, 'gold'); px(d, 8, 8, 'gold'); [px(d, 4 + i, 1 + i, 'dkbrown') for i in range(5)]
    if kind == 'streak': disc(d, 7, 8, 5, 'terra'); disc(d, 7, 9, 3, 'gold'); px(d, 7, 2, 'terra_lt'); px(d, 6, 3, 'terra')
    if kind == 'scroll': rect(d, 3, 3, 12, 12, 'parch'); rect(d, 2, 2, 13, 3, 'tan'); rect(d, 2, 12, 13, 13, 'tan'); [rect(d, 5, y, 10, y, 'ltbrown') for y in (5, 7, 9)]
    return outline(im)

def ui_frame():
    """24x24 nine-slice frame (8px corners) — parchment with a terracotta key-pattern border."""
    im = img(24, 24, C('parch')); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 23, 23], outline=C('dkbrown')); d.rectangle([1, 1, 22, 22], outline=C('terra'))
    d.rectangle([3, 3, 20, 20], outline=C('terra_dk'))
    for c in ((2, 2), (21, 2), (2, 21), (21, 21)): px(d, c[0], c[1], 'gold')
    return im

def ui_tablet():
    im = img(48, 24); d = ImageDraw.Draw(im)
    rect(d, 1, 1, 46, 22, 'marble'); d.rectangle([3, 3, 44, 20], outline=C('stone_lt'))
    rect(d, 0, 9, 1, 14, 'stone_lt'); rect(d, 46, 9, 47, 14, 'stone_lt')
    return outline(im)

def font_roman():
    """Bitmap font: glyphs I V X L C D M, each 5x7, plus a 1px gap; total 7 cols x 6px = 42x7."""
    G = {'I': ['11111', '00100', '00100', '00100', '00100', '00100', '11111'],
         'V': ['10001', '10001', '10001', '10001', '01010', '01010', '00100'],
         'X': ['10001', '10001', '01010', '00100', '01010', '10001', '10001'],
         'L': ['10000', '10000', '10000', '10000', '10000', '10000', '11111'],
         'C': ['01111', '10000', '10000', '10000', '10000', '10000', '01111'],
         'D': ['11110', '10001', '10001', '10001', '10001', '10001', '11110'],
         'M': ['10001', '11011', '10101', '10101', '10001', '10001', '10001']}
    im = img(42, 7); d = ImageDraw.Draw(im)
    for k, ch in enumerate('IVXLCDM'):
        for y, row in enumerate(G[ch]):
            for x, b in enumerate(row):
                if b == '1': px(d, k * 6 + x, y, 'ink')
    return im

def app_icon(size):
    im = img(32, 32, C('terra_dk')); d = ImageDraw.Draw(im)
    rect(d, 2, 2, 29, 29, 'terra')
    # laurel wreath around an "L"
    for i in range(10):
        a = math.pi * (0.62 + 0.76 * i / 9)
        for side in (-1, 1):
            x = 16 + side * int(round(11 * math.cos(a - math.pi / 2) * -1)); y = 16 + int(round(11 * math.sin(a - math.pi / 2) * -1))
            x = 16 + int(round(10 * math.cos(a))) * side * -1 if False else x
    for t in range(14):
        ang = math.radians(110 + t * 10)
        for side in (1, -1):
            x = 16 + side * int(round(10 * math.cos(ang))); y = 17 - int(round(10 * math.sin(ang)))
            px(d, x, y, 'sage'); px(d, x + side, y - 1, 'leaf')
    rect(d, 12, 9, 14, 22, 'cream'); rect(d, 12, 20, 20, 22, 'cream'); rect(d, 11, 9, 15, 9, 'cream')
    big = im.resize((size, size), Image.NEAREST)
    return big

# ---------------------------------------------------------------- specs
DISTRICTS = {
    'provinciae': ('The provinces of the Empire (chapter I)', 'an old parchment map-land: pale sand, faint contour specks'),
    'villa': ('The family villa and household', 'trimmed grass and garden borders around the villa'),
    'hortus': ('The garden (hortus) and peristyle', 'lush garden ground with flowers (roses, lilies)'),
    'via': ('The Via Latina toward Tusculum', 'roadside meadow, dusty verges'),
    'taberna': ('The shops of Rome', 'packed earth and paving in front of shops'),
    'rus': ('Farm and countryside', 'fields with furrows, pasture'),
    'silva': ('Forest of wild beasts', 'dark forest floor'),
    'castra': ('Army camp / frontier', 'trampled earth of a legionary camp'),
    'templa': ('Temples and the calendar', 'marble paving'),
    'ludus': ('The school (ludus)', 'stone floor of a schoolroom portico'),
    'mare': ('Harbor and open sea', 'sea water with small waves'),
    'urbs': ('Streets of Rome', 'basalt street paving'),
    'creta': ('Crete and the Labyrinth (myth)', 'ochre Cretan earth'),
    'caelum': ('Cliffs and sky (Daedalus and Icarus)', 'pale sky with clouds'),
    'triclinium': ('The dining room (banquet)', 'mosaic floor in deep reds'),
    'theatrum': ('Theater and circus', 'sand of the arena'),
    'forum': ('The Forum and the Capitol (finale)', 'gleaming marble and gold-flecked paving'),
}
PROPS = ['cypress', 'pine', 'olive', 'bush', 'column', 'statue', 'house', 'shop', 'sheep', 'rock', 'vine', 'wheat', 'boat',
         'wave', 'tent', 'standard', 'amphora', 'bench', 'templum', 'wall', 'labyrinth', 'cloud', 'feather', 'couch', 'lamp', 'mask', 'arena']
PROP_DESC = {
    'cypress': 'tall slender Italian cypress', 'pine': 'Italian umbrella (stone) pine', 'olive': 'olive tree, silvery leaves',
    'bush': 'low shrub with a few rose blossoms', 'column': 'single marble column', 'statue': 'marble statue on a plinth',
    'house': 'small Roman house with terracotta roof', 'shop': 'taberna (shop front) with striped awning and goods',
    'sheep': 'white sheep (pastor et ovēs)', 'rock': 'grey boulder', 'vine': 'grapevine on a trellis with purple grapes',
    'wheat': 'patch of ripe wheat', 'boat': 'merchant ship with a square sail', 'wave': 'small wave crest (decor on water)',
    'tent': 'leather legionary tent with pennant', 'standard': 'legion standard (aquila) with red banner', 'amphora': 'clay amphora',
    'bench': 'school bench with a wax tablet', 'templum': 'small temple facade', 'wall': 'crenellated stone wall segment',
    'labyrinth': 'labyrinth pattern stone (Crete)', 'cloud': 'small cloud', 'feather': 'loose feather (Icarus)',
    'couch': 'dining couch (lectus triclinii)', 'lamp': 'standing oil lamp', 'mask': 'theatre mask', 'arena': 'small circus/arena oval'}
DISTRICT_PROPS = {
    'provinciae': ['cypress', 'rock', 'olive', 'templum'], 'villa': ['house', 'cypress', 'bush', 'column', 'amphora'],
    'hortus': ['bush', 'olive', 'statue', 'column'], 'via': ['cypress', 'pine', 'rock', 'house'],
    'taberna': ['shop', 'amphora', 'house', 'lamp'], 'rus': ['sheep', 'wheat', 'olive', 'vine', 'rock'],
    'silva': ['pine', 'cypress', 'rock', 'bush'], 'castra': ['tent', 'standard', 'wall', 'rock'],
    'templa': ['templum', 'column', 'statue', 'cypress'], 'ludus': ['bench', 'column', 'statue', 'lamp'],
    'mare': ['boat', 'wave', 'wave', 'rock'], 'urbs': ['house', 'shop', 'column', 'lamp'],
    'creta': ['labyrinth', 'rock', 'olive', 'column'], 'caelum': ['cloud', 'feather', 'cloud', 'rock'],
    'triclinium': ['couch', 'amphora', 'lamp', 'column'], 'theatrum': ['mask', 'arena', 'column', 'statue'],
    'forum': ['templum', 'column', 'statue', 'cypress']}
CHAPTER_DISTRICT = ['provinciae', 'villa', 'villa', 'villa', 'hortus', 'via', 'hortus', 'taberna', 'rus', 'silva', 'villa', 'castra',
                    'templa', 'villa', 'ludus', 'mare', 'ludus', 'ludus', 'forum', 'villa', 'urbs', 'villa', 'ludus', 'villa',
                    'creta', 'caelum', 'rus', 'mare', 'mare', 'triclinium', 'triclinium', 'mare', 'castra', 'theatrum', 'forum']

specs = []
def add(id_, file, im_fn, w, h, frames, use, desc, fps=None, extra=None):
    specs.append(dict(id=id_, file=file, w=w, h=h, frames=frames, fps=fps, use=use, desc=desc, _fn=im_fn, **(extra or {})))

hero_desc = ('Sprite sheet, 6 columns x 4 rows of 16x24 frames. Columns: idle 0, idle 1, walk 0-3. Rows: facing down, up, left, right. '
             'Feet at the bottom-centre of each frame (anchor 8,23).')
add('hero_base', 'sprites/hero_base.png', lambda: hero_sheet('base'), 16, 24, 6,
    'Map: the player character (always drawn)', 'A young Roman in a cream tunic with a belt and sandals, dark hair. ' + hero_desc, fps=8,
    extra={'rows': ['down', 'up', 'left', 'right'], 'anim': {'idle': [0, 1], 'walk': [2, 3, 4, 5]}, 'anchor': [8, 23]})
for layer, d_ in (('toga', 'white toga with a purple border (toga praetexta) draped over the tunic'),
                  ('cloak', 'terracotta travelling cloak (paenula) with a gold clasp'),
                  ('laurel', 'green laurel wreath on the head (final reward)'),
                  ('satchel', 'leather school satchel (capsa) on a strap')):
    add(f'hero_{layer}', f'sprites/hero_{layer}.png', (lambda l=layer: hero_sheet(l)), 16, 24, 6,
        f'Map: outfit layer drawn over hero_base when equipped', f'Overlay layer: {d_}. Same frame layout as hero_base; transparent elsewhere.', fps=8,
        extra={'rows': ['down', 'up', 'left', 'right'], 'anim': {'idle': [0, 1], 'walk': [2, 3, 4, 5]}, 'anchor': [8, 23]})
add('tile_via', 'tiles/tile_via.png', tile_via, 16, 16, 1, 'Map: the stone-paved road (repeating texture along the path)',
    'Seamless tile of Roman basalt paving stones (polygonal blocks), grey with darker joints.')
for k, (title, d_) in DISTRICTS.items():
    add(f'bg_{k}', f'tiles/bg_{k}.png', (lambda k=k: bg_tile(k)), 32, 32, 1, f'Map background, district: {title}',
        f'Seamless ground tile: {d_}.')
for k in PROPS:
    tmp = prop(k)
    add(f'prop_{k}', f'props/prop_{k}.png', (lambda k=k: prop(k)), tmp.size[0], tmp.size[1], 1,
        'Map decoration scattered beside the road in districts: ' + ', '.join(d for d, ps in DISTRICT_PROPS.items() if k in ps),
        PROP_DESC[k] + '. Anchor at bottom centre.')
for k, (w, h, d_, u) in {'milestone': (10, 18, 'Roman milestone (miliarium), cylindrical stone; the week number is drawn on it with font_roman', 'Map: every rest stop (one per week)'),
                         'fountain': (24, 20, 'public fountain with a basin and a spout', 'Map: rest stop (catch-up day), alternates with shrine'),
                         'shrine': (20, 24, 'small roadside shrine (lararium/aedicula) with a gilded image', 'Map: rest stop (catch-up day), alternates with fountain'),
                         'arch': (48, 40, 'triumphal arch spanning the road, gold inscription panel on top', 'Map: end of every chapter'),
                         'capitolium': (96, 72, 'Temple of Jupiter on the Capitoline: wide steps, columns, gilded pediment', 'Map: final destination (end of chapter XXXV)')}.items():
    add(f'landmark_{k}', f'landmarks/landmark_{k}.png', (lambda k=k: landmark(k)), w, h, 1, u, d_ + '. Anchor at bottom centre.')
for k, d_ in (('locked', 'dim grey stepping stone (future day, locked)'), ('current', 'glowing golden marker (today\'s unlocked stop)'),
              ('done', 'terracotta stamped marker with a gold dot (completed day)'), ('rest', 'blue-grey marker for rest stops')):
    add(f'wp_{k}', f'ui/wp_{k}.png', (lambda k=k: waypoint(k)), 12, 12, 1, 'Map: waypoint marker on the road', d_ + '.')
for k, d_ in (('as', 'bronze as'), ('dupondius', 'brass dupondius'), ('sestertius', 'orichalcum sestertius'), ('quinarius', 'small silver quinarius'),
              ('denarius', 'silver denarius'), ('aureus', 'gold aureus')):
    add(f'coin_{k}', f'ui/coin_{k}.png', (lambda k=k: coin(k)), 12, 12, 1, 'Rewards screen: streak coin', f'A {d_} seen face-on, with a simple portrait or emblem.')
for k, d_ in (('tunic', 'tunic'), ('toga', 'folded toga with purple border'), ('cloak', 'travelling cloak'), ('laurel', 'laurel wreath'),
              ('satchel', 'school satchel'), ('streak', 'small flame / hearth for the streak counter'), ('scroll', 'scroll for "words learned"')):
    add(f'icon_{k}', f'ui/icon_{k}.png', (lambda k=k: icon(k)), 16, 16, 1, 'UI icon (wardrobe, stats)', f'Icon: {d_}.')
add('ui_frame', 'ui/ui_frame.png', ui_frame, 24, 24, 1, 'UI: 9-slice frame for chapter title cards and panels (8px slices)',
    'Parchment panel with a terracotta double border and gold corner studs. Must work as CSS border-image with 8px slices.', extra={'slice': 8})
add('ui_tablet', 'ui/ui_tablet.png', ui_tablet, 48, 24, 1, 'Rewards screen: background of each collected chapter inscription',
    'Marble inscription tablet (tabula ansata) with a carved inner border; text is overlaid by the app.')
add('font_roman', 'ui/font_roman.png', font_roman, 5, 7, 7, 'Map: Roman numerals on milestones and arches',
    'Bitmap font sheet: glyphs I V X L C D M in that order, each 5x7, separated by 1px (sheet 42x7). Dark ink colour.',
    extra={'glyphs': 'IVXLCDM', 'advance': 6})
for s in (180, 192, 512):
    add(f'app_icon_{s}', f'icons/icon-{s}.png', (lambda s=s: app_icon(s)), s, s, 1, 'Home-screen / PWA icon',
        'App icon: a laurel wreath around a cream letter L on a terracotta field, pixel-art style (32x32 art upscaled ×%d).' % (s // 32 or 1),
        extra={'root': True})

def main():
    os.makedirs(OUT, exist_ok=True)
    manifest = {'version': 1, 'note': 'All visual assets. The app reads only this file; replace PNGs (same size) or edit entries to swap art.',
                'palette': P, 'chapterDistricts': CHAPTER_DISTRICT,
                'districts': {k: {'title': t, 'bg': f'bg_{k}', 'props': [f'prop_{p}' for p in DISTRICT_PROPS[k]]} for k, (t, d) in DISTRICTS.items()},
                'assets': {}}
    total = 0
    for s in specs:
        path = os.path.join(ROOT, s['file']) if s.get('root') else os.path.join(OUT, s['file'])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not (KEEP and os.path.exists(path)):
            im = s['_fn'](); im.save(path, optimize=True)
        total += os.path.getsize(path)
        e = {k: v for k, v in s.items() if not k.startswith('_') and k not in ('desc', 'use', 'root') and v is not None}
        e['file'] = ('../' + s['file']) if s.get('root') else s['file']
        e['use'] = s['use']; e['desc'] = s['desc']
        manifest['assets'][s['id']] = e
    json.dump(manifest, open(os.path.join(OUT, 'assets.json'), 'w'), indent=1, ensure_ascii=False)
    write_guide(manifest, total)
    print(len(specs), 'assets', round(total / 1024, 1), 'KB')

def write_guide(m, total):
    L = []
    L.append('# ART GUIDE — "Via Romana" map and sprites\n')
    L.append('This is the brief for the final pixel-art pass. The app currently ships simple placeholder art drawn by '
             '`tools/make_placeholder_art.py`. **Swapping art needs no code changes:** replace each PNG at the same path and size, '
             'or edit its entry in `assets/assets.json` (file, size, frame count, fps, anchor). The app reads nothing else.\n')
    L.append('## Style\n')
    L.append('- Dignified retro pixel art, 16/32-bit era (think late SNES / early GBA), warm earthy palette. Nothing cartoonish or candy-coloured.\n'
             '- Hard pixel edges, no anti-aliasing, no semi-transparent pixels except where noted. Transparent PNG backgrounds.\n'
             '- Sprites use a 1px dark outline (`ink` #2b1d16) or selective outlining.\n'
             '- Light comes from the upper left.\n'
             '- The map is drawn at an integer scale (×2 on iPhones, ×3 on larger screens) with nearest-neighbour scaling.\n'
             '- Total asset budget: keep everything under 5 MB (currently %.0f KB).\n' % (total / 1024))
    L.append('## Palette (32 colours)\n')
    L.append('Placeholders use only these colours; the final art may extend the palette but should stay within this warm family.\n')
    L.append('| name | hex | name | hex |\n|---|---|---|---|')
    items = list(m['palette'].items())
    for i in range(0, len(items), 2):
        a = items[i]; b = items[i + 1] if i + 1 < len(items) else ('', '')
        L.append(f'| {a[0]} | `{a[1]}` | {b[0]} | `{b[1]}` |')
    L.append('\n## Map layout (how assets are used)\n')
    L.append('- The map is a tall vertical scroll. The road (`tile_via`) winds upward from chapter I at the bottom to the Capitol at the top.\n'
             '- 364 stops: 312 reading days + 52 rest stops (one after every 6 reading days). Each rest stop shows `landmark_fountain` or `landmark_shrine` (alternating) plus a `landmark_milestone` with the week number in Roman numerals (`font_roman`).\n'
             '- Each chapter is a district: its ground is the district tile (`bg_*`), decorated with that district\'s props scattered beside the road. '
             'A `landmark_arch` stands at the end of every chapter; the chapter title card (HTML, framed by `ui_frame`) appears when entering a new district.\n'
             '- `landmark_capitolium` crowns the very top (end of chapter XXXV).\n'
             '- Waypoints: `wp_done`, `wp_current`, `wp_locked`, `wp_rest`.\n'
             '- The player is `hero_base` with optional overlay layers (`hero_toga`, `hero_cloak`, `hero_satchel`, `hero_laurel`) drawn in that order.\n')
    L.append('### Chapter → district\n')
    L.append('| chapter | district |\n|---|---|')
    for i, dname in enumerate(m['chapterDistricts']):
        L.append(f'| {i + 1} | `{dname}` — {m["districts"][dname]["title"]} |')
    L.append('\n## Asset list\n')
    L.append('| id | file | size (px) | frames | where it appears | what it depicts |\n|---|---|---|---|---|---|')
    for k, a in m['assets'].items():
        fr = a.get('frames', 1)
        size = f"{a['w']}×{a['h']}" + (f" per frame (sheet {a['w']*fr}×{a['h']*len(a.get('rows', [1]))})" if fr > 1 and k.startswith('hero') else '')
        if k == 'font_roman': size = '5×7 per glyph (sheet 42×7)'
        L.append(f"| `{k}` | `{a['file']}` | {size} | {fr}{(' @ ' + str(a['fps']) + ' fps') if a.get('fps') else ''} | {a['use']} | {a['desc']} |")
    L.append('\n## Animation notes\n')
    L.append('- `hero_*` sheets: columns = [idle0, idle1, walk0, walk1, walk2, walk3]; rows = [down, up, left, right]. The `anim` field in assets.json maps animation names to column indices — you may add frames and update `frames`/`anim`.\n'
             '- Walk cycle plays at `fps` while the character moves between waypoints; idle alternates slowly (the app halves the fps for idle).\n')
    L.append('\n## Checklist for the artist\n')
    L.append('1. Keep each file name and pixel size (or update assets.json to match).\n2. Keep transparent backgrounds for sprites/props/landmarks; tiles must be seamless.\n'
             '3. Run `node tools/validate.mjs` afterwards: it checks every asset in assets.json exists and matches its declared size.\n')
    open(os.path.join(ROOT, 'ART_GUIDE.md'), 'w').write('\n'.join(L) + '\n')

if __name__ == '__main__':
    main()
