#!/usr/bin/env python3
"""Final pixel art for Via Latina.

Every sprite is a hand-authored character grid: one character is one pixel, mapped to the
palette in CH below. Larger buildings are assembled from hand-authored parts (a column, a
row of roof tiles, a pediment half) so that each pixel is still intentional. Only the
seamless ground tiles use seeded noise, and the seed is fixed, so every run produces
byte-identical art.

    python3 tools/make_final_art.py                  write assets/** and icons/**, sync assets.json
    python3 tools/make_final_art.py --sheet out.png  also write a 4x contact sheet of everything
    python3 tools/make_final_art.py --check          build everything in memory, write nothing

Needs Pillow. The script only rewrites the size / frame / anchor fields of assets.json that
it owns (see MANIFEST at the bottom); descriptions and the district lists are left alone.
"""
import json, math, os, random, sys
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, 'assets')

# ------------------------------------------------------------------ palette
# The 32 colours of ART_GUIDE.md plus six in-family extras (marked +).
PAL = {
    'ink': '#2b1d16', 'dkbrown': '#4a3426', 'brown': '#6b4a32', 'ltbrown': '#8f6a48',
    'tan': '#b8916a', 'sand': '#d9bf8f', 'parch': '#ecdcb3', 'cream': '#f6ecd2',
    'terra_dk': '#7a3223', 'terra': '#a84a2f', 'terra_lt': '#c96f47', 'ochre': '#c9962f',
    'gold': '#e0b84a', 'olive_dk': '#3c4a24', 'olive': '#5d6b34', 'sage': '#8a9455',
    'leaf': '#b0b57a', 'stone_dk': '#5a5550', 'stone': '#8a847a', 'stone_lt': '#b5ad9e',
    'marble': '#ddd6c8', 'sea_dk': '#23394a', 'sea': '#3e5f73', 'sea_lt': '#6f8f9c',
    'sky': '#a9bfc4', 'wine': '#5e2333', 'purple': '#5a3a5e', 'white': '#f8f4ea',
    'black': '#140e0b', 'skin': '#c98f62', 'skin_dk': '#9c6440', 'red': '#8e2b22',
    # + extras
    'gold_lt': '#f3dc8c', 'forest': '#2b3620', 'marble_dk': '#c7bfb0', 'skin_lt': '#e0ab7e',
    'bronze': '#7c5a2c', 'foam': '#cfe0df',
}
EXTRA = ['gold_lt', 'forest', 'marble_dk', 'skin_lt', 'bronze', 'foam']

# one character = one pixel
CH = {
    '.': None,
    'k': 'ink', 'K': 'black', 'B': 'dkbrown', 'b': 'brown', 'l': 'ltbrown', 't': 'tan',
    'n': 'sand', 'p': 'parch', 'c': 'cream', 'w': 'white',
    'R': 'terra_dk', 'r': 'terra', 'o': 'terra_lt', 'x': 'red',
    'y': 'ochre', 'g': 'gold', 'E': 'gold_lt', 'z': 'bronze',
    'Z': 'forest', 'G': 'olive_dk', 'v': 'olive', 'e': 'sage', 'f': 'leaf',
    'D': 'stone_dk', 's': 'stone', 'S': 'stone_lt', 'M': 'marble_dk', 'm': 'marble',
    'N': 'sea_dk', 'a': 'sea', 'A': 'sea_lt', 'Y': 'sky', 'F': 'foam',
    'W': 'wine', 'P': 'purple',
    'h': 'skin', 'H': 'skin_dk', 'i': 'skin_lt',
}

def rgb(name):
    h = PAL[name].lstrip('#')
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 255)

def mix(a, b, t):
    """a colour t of the way from palette colour a to b (tile textures only)"""
    A, B = rgb(a), rgb(b)
    return tuple(round(A[i] + (B[i] - A[i]) * t) for i in range(3)) + (255,)

CLEAR = (0, 0, 0, 0)
RGB = {c: (rgb(n) if n else CLEAR) for c, n in CH.items()}

def new(w, h, fill=CLEAR):
    return Image.new('RGBA', (w, h), fill)

def rows_of(text):
    return [ln.strip() for ln in text.strip().splitlines()]

def G(text, name='?', remap=None):
    """parse a character grid into an image"""
    rows = rows_of(text)
    w = len(rows[0])
    im = new(w, len(rows)); px = im.load()
    for y, row in enumerate(rows):
        if len(row) != w:
            raise SystemExit(f'grid {name}: row {y} is {len(row)} wide, expected {w}: {row}')
        for x, c in enumerate(row):
            if remap and c in remap: c = remap[c]
            if c not in RGB:
                raise SystemExit(f'grid {name}: unknown character {c!r} in row {y}')
            px[x, y] = RGB[c]
    return im

def put(dst, src, x=0, y=0):
    """stamp src onto dst at (x, y); pixels are either opaque or fully transparent"""
    sw, sh = src.size; dw, dh = dst.size
    s = src.load(); d = dst.load()
    for j in range(sh):
        yy = y + j
        if not 0 <= yy < dh: continue
        for i in range(sw):
            xx = x + i
            if 0 <= xx < dw and s[i, j][3]:
                d[xx, yy] = s[i, j]
    return dst

def flip(im):
    return im.transpose(Image.FLIP_LEFT_RIGHT)

def mirror_h(text):
    """mirror a half-grid: each row gets its reverse appended (for symmetric architecture)"""
    return '\n'.join(r + r[::-1] for r in rows_of(text))

BUILDERS = []
OUT = {}       # asset id -> image
META = {}      # asset id -> fields to sync into assets.json

def asset(aid, im, **meta):
    OUT[aid] = im
    META[aid] = meta
    return im

# ================================================================== HERO
# 16x24 frames, anchor at the feet (8,23). Sheet: 6 columns (idle0, idle1, walk0-3) by
# 4 rows (down, up, left, right). Each frame is assembled from an "upper" (head, torso,
# rows 0-17), a pair of legs (rows 18-23) and, in the side views, a swinging arm.
# The upper drops one pixel on the idle breath and on the two contact frames of the walk;
# every outfit layer rides on the same offset, so layers always line up with the base.

UP_D = """
................
.....kkkkkk.....
....kbbBBBBk....
....kbBBBBBk....
....kBhhhhBk....
....khkhhkHk....
....khhhhhHk....
.....khhhHk.....
....kkkHHkkk....
...kccccccppk...
...kccccccppk...
...khcccccpHk...
...khcccccpHk...
...khbbbbbBHk...
...khcccccpHk...
...kkccccppkk...
....kcpccpnk....
....kkkkkkkk....
"""
UP_U = """
................
.....kkkkkk.....
....kbbBBBBk....
....kbBBBBBk....
....kBBBBBBk....
....kBBBBBBk....
....kBBBBBBk....
.....kHhhHk.....
....kkkHHkkk....
...kccccccppk...
...kccccccppk...
...khcccccpHk...
...khcccccpHk...
...khbbbbbBHk...
...khcccccpHk...
...kkccccppkk...
....kcpccpnk....
....kkkkkkkk....
"""
UP_S = """
................
.....kkkkkk.....
....kbbBBBBk....
....kbBBBBBBk...
....khhhBBBBk...
....khkhHBBBk...
....khhhhHHBk...
.....khhhHHk....
.....kkkHHkk....
....kcccccpk....
....kcccccpk....
....kcccccpk....
....kcccccpk....
....kbbbbbBk....
....kcccccpk....
....kccccppk....
....kcpccpnk....
....kkkkkkkk....
"""
ARM_S = {
    'idle': """
................
................
................
................
................
................
................
................
................
................
.......pn.......
.......hHn......
.......hHn......
.......hHn......
.......hHk......
.......kk.......
................
................
""",
    'fwd': """
................
................
................
................
................
................
................
................
................
................
.......pn.......
......hHn.......
......hHn.......
.....hHn........
...khHk.........
....kk..........
................
................
""",
    'back': """
................
................
................
................
................
................
................
................
................
................
.......pn.......
........hHn.....
........hHn.....
.........hHk....
..........hHk...
..........kk....
................
................
""",
}
LEGS_D = {
    'stand': """
....kHHkkHHk....
....khhkkhHk....
....khhkkhHk....
....kbbkkbBk....
....khhkkhHk....
....kkkkkkkk....
""",
    'a': """
....kHHkkHHk....
....khhkkHHk....
....khhkkbBk....
....kbbkkHHk....
....khhkkkkk....
....kkkk........
""",
    'b': """
....kHHkkHHk....
....kHHkkhHk....
....kbbkkhHk....
....kHHkkbBk....
....kkkkkhHk....
........kkkk....
""",
}
LEGS_S = {
    'stand': """
......kHHk......
......khHk......
......khHk......
......kbBk......
.....khhHk......
.....kkkkk......
""",
    'a': """
.....kHHHHk.....
....khhkkHHk....
...khhk..kHHk...
...kbbk..kBBk...
..khhhk..kHHk...
..kkkkk..kkkk...
""",
    'b': """
.....kHHHHk.....
....kHHkkhhk....
...kHHk..khhk...
...kBBk..kbbk...
..kHHHk..khhk...
..kkkkk..kkkk...
""",
    'pass1': """
......kHHk......
......khHk......
......khHkk.....
......kbBHk.....
.....khhkk......
.....kkkk.......
""",
    'pass2': """
......kHHk......
......khhk......
.....khhHk......
.....kbbHk......
......kkBBk.....
.......kkkk.....
""",
}

# ---- outfit layers (same coordinates as the uppers; 20 rows so the toga can hang lower)
CLOAK = {
    'd': """
................
................
................
................
................
................
................
................
....kor..rRk....
...koorggrrRk...
..kooorrrrrrRk..
..koorrrrrrrRk..
..koorrrRrrrRk..
..korrrrRrrRRk..
..korrrrRrrRRk..
...kkrrrRrRkk...
......kRRk......
................
................
................
""",
    'u': """
................
................
................
................
................
................
................
................
....koRRRRRk....
...kooRrrrRRk...
..kooorRrrRrRk..
..koorrrRRrrRk..
..koorrrRrrrRk..
..korrrrRrrRRk..
..korrrrRrrRRk..
...kkrrrRrRkk...
......kRRk......
................
................
................
""",
    's': """
................
................
................
................
................
................
................
................
................
....kgorrrRk....
...koorrrrrRk...
...koorrrrrRk...
..koorrrrrrRRk..
..koorrrrRrRRk..
..korrrrrRrRRk..
..kkkkkkkkkkkk..
................
................
................
................
""",
}
TOGA = {
    'd': """
................
................
................
................
................
................
................
................
................
.........Pwmk...
........Pwwmmk..
.......Pwwmwmk..
......Pwwmwwmk..
.....Pwwmwwmmk..
.....wwmwwwmSk..
....kwmwwwmwSk..
...kwwmwwwmwSk..
...kwmwwwmwwSk..
...kPPPPPPPPWk..
...kkkkkkkkkkk..
""",
    'u': """
................
................
................
................
................
................
................
................
................
...kwwP.........
..kwwwmP........
..kwwmwwP.......
..kwwmwwmP......
..kwmwwmwwP.....
..kwmwwmwww.....
..kwmwwmwwmk....
..kwwmwwwmwSk...
..kwmwwwmwwSk...
..kPPPPPPPPWk...
..kkkkkkkkkkk...
""",
    # the figure's left side (seen when he faces left): arm and shoulder fully draped
    'sl': """
................
................
................
................
................
................
................
................
................
....kwwwwwmk....
...kPwwmwwmmk...
...kPwmwwmwmk...
...kPwmwwmwmk...
...kPwmwmwwmk...
...kwwmwmwwmk...
...kwmwwmwmSk...
...kwmwwmwmSk...
...kwmwmwwmSk...
...kPPPPPPPWk...
...kkkkkkkkkk...
""",
    # the figure's right side (seen when he faces right): the right arm stays bare
    'sr': """
................
................
................
................
................
................
................
................
................
....kPw.........
....kwP.........
....kwwP........
....kwmwPPPk....
...kwwmwwmwmk...
...kwmwwmwwmk...
...kwmwwmwmSk...
...kwmwwmwmSk...
...kwmwmwwmSk...
...kPPPPPPPWk...
...kkkkkkkkkk...
""",
}
SATCHEL = {
    'd': """
................
................
................
................
................
................
................
................
................
.....B..........
......B.........
.......B........
........B.......
.........kkkk...
........ktllBk..
........klglBk..
........klllBk..
.........kkkk...
................
................
""",
    'u': """
................
................
................
................
................
................
................
................
................
..........B.....
.........B......
........B.......
.......B........
...kkkk.........
..ktllBk........
..klllBk........
..klllBk........
...kkkk.........
................
................
""",
    'sl': """
................
................
................
................
................
................
................
................
................
......B.........
......B.........
.......B........
.......B........
......kkkk......
.....ktllBk.....
.....klglBk.....
.....klllBk.....
......kkkk......
................
................
""",
    'sr': """
................
................
................
................
................
................
................
................
................
........B.......
........B.......
.........B......
.........B......
..........Bkk...
...........lBk..
...........lBk..
...........lBk..
...........kkk..
................
................
""",
}
LAUREL = {
    'd': """
................
................
...fe......ef...
...efve..evfe...
................
................
................
................
................
................
................
................
................
................
................
................
................
................
................
................
""",
    'u': """
................
................
...fe......ef...
...efvefevefe...
.......xx.......
................
................
................
................
................
................
................
................
................
................
................
................
................
................
................
""",
    's': """
................
................
...fe....efe....
....efvefevfe...
................
................
................
................
................
................
................
................
................
................
................
................
................
................
................
................
""",
}

# column -> (drop of the upper, legs, arm) for the front/back views and the side view
FRAMES = [
    ('idle0', 0, 'stand', 'idle'),
    ('idle1', 1, 'stand', 'idle'),
    ('walk0', 1, 'a', 'back'),
    ('walk1', 0, 'pass1', 'idle'),
    ('walk2', 1, 'b', 'fwd'),
    ('walk3', 0, 'pass2', 'idle'),
]
HERO_ROWS = ['down', 'up', 'left', 'right']
FW, FH = 16, 24

def hero_frame(layer, direction, col):
    _, drop, legs, arm = FRAMES[col]
    f = new(FW, FH)
    side = direction in ('left', 'right')
    if layer == 'base':
        if side:
            put(f, G(LEGS_S[legs], 'legs_s'), 0, 18)
            put(f, G(UP_S, 'up_s'), 0, drop)
            put(f, G(ARM_S[arm], 'arm'), 0, drop)
        else:
            lg = legs if legs in LEGS_D else 'stand'
            put(f, G(LEGS_D[lg], 'legs_d'), 0, 18)
            put(f, G(UP_D if direction == 'down' else UP_U, 'up'), 0, drop)
    else:
        table = {'cloak': CLOAK, 'toga': TOGA, 'satchel': SATCHEL, 'laurel': LAUREL}[layer]
        key = {'down': 'd', 'up': 'u', 'left': 'sl', 'right': 'sr'}[direction]
        if key not in table: key = 's'
        put(f, G(table[key], layer + '_' + key), 0, drop)
        if layer == 'toga' and direction == 'right':
            put(f, G(ARM_S[arm], 'arm'), 0, drop)      # bare right arm swings over the drape
    return flip(f) if direction == 'right' else f

def hero_sheet(layer):
    sheet = new(FW * len(FRAMES), FH * len(HERO_ROWS))
    for r, direction in enumerate(HERO_ROWS):
        for c in range(len(FRAMES)):
            put(sheet, hero_frame(layer, direction, c), c * FW, r * FH)
    return sheet

def build_hero():
    for layer in ('base', 'cloak', 'toga', 'satchel', 'laurel'):
        asset('hero_' + layer, hero_sheet(layer), w=FW, h=FH, frames=len(FRAMES), fps=8,
              rows=HERO_ROWS, anim={'idle': [0, 1], 'walk': [2, 3, 4, 5]}, anchor=[8, 23])

BUILDERS.append(build_hero)

# ================================================================== TILES
# Ground tiles are the one place where texture is generated: a flat base colour plus sparse,
# low-contrast marks placed by a fixed-seed jittered grid, wrapped at the edges so the tile
# repeats without a seam. They are 64x64 so the repeat is hard to spot across a phone screen.
class Tile:
    def __init__(self, w, h, base, seed):
        self.w, self.h = w, h
        self.im = new(w, h, base); self.px = self.im.load()
        self.r = random.Random(seed)
    def rnd(self): return self.r.random()
    def ri(self, n): return int(self.r.random() * n)
    def pick(self, seq): return seq[self.ri(len(seq))]
    def set(self, x, y, col): self.px[x % self.w, y % self.h] = col
    def get(self, x, y): return self.px[x % self.w, y % self.h]
    def spots(self, step, prob):
        """one candidate position per step x step cell: evenly spread, never clumped"""
        out = []
        for gy in range(0, self.h, step):
            for gx in range(0, self.w, step):
                x, y = gx + self.ri(step), gy + self.ri(step)
                if self.rnd() < prob: out.append((x, y))
        return out
    def stamp(self, x, y, shape):
        for dx, dy, c in shape: self.set(x + dx, y + dy, c)

def t_provinciae():
    t = Tile(64, 64, mix('parch', 'sand', .45), 11)
    lo, hi = mix('sand', 'tan', .22), mix('parch', 'cream', .45)
    for x, y in t.spots(4, .20): t.set(x, y, hi)
    for x, y in t.spots(5, .16): t.set(x, y, lo)
    for x, y in t.spots(16, .75):                      # faint contour strokes of an old map
        n = 3 + t.ri(3)
        for i in range(n): t.set(x + i, y + (1 if i >= n - 1 else 0), lo)
    return t.im

def grass(base, dark, light, seed, dp=.42, lp=.28):
    t = Tile(64, 64, base, seed)
    for x, y in t.spots(5, dp):
        t.stamp(x, y, t.pick([[(0, 0, dark), (1, -1, dark)], [(0, 0, dark), (0, -1, dark)], [(0, 0, dark), (-1, -1, dark)]]))
    for x, y in t.spots(6, lp):
        t.stamp(x, y, t.pick([[(0, 0, light)], [(0, 0, light), (1, 0, light)]]))
    return t

def t_villa():
    return grass(mix('sage', 'olive', .28), mix('sage', 'olive', .58), mix('sage', 'leaf', .42), 21).im

def t_hortus():
    t = grass(mix('olive', 'sage', .50), mix('olive', 'olive_dk', .35), mix('sage', 'leaf', .25), 31, .5, .4)
    rose = [(0, 0, rgb('terra_lt')), (1, 0, rgb('red')), (0, 1, rgb('red'))]
    lily = [(0, 0, rgb('cream')), (1, 0, rgb('parch')), (0, 1, rgb('ochre'))]
    for i, (x, y) in enumerate(t.spots(16, .7)):
        t.stamp(x, y, rose if i % 2 else lily)
    return t.im

def t_via():
    t = grass(mix('leaf', 'sand', .55), mix('leaf', 'sage', .55), mix('sand', 'parch', .4), 41, .30, .22)
    dust = mix('sand', 'parch', .15)
    for x, y in t.spots(16, .6):                       # dusty bare patches
        w = 4 + t.ri(4)
        for i in range(w):
            t.set(x + i, y, dust)
            if 0 < i < w - 1: t.set(x + i, y + 1, dust)
    for x, y in t.spots(11, .3): t.set(x, y, mix('tan', 'sand', .3))
    return t.im

def t_taberna():
    base = mix('tan', 'sand', .55)
    t = Tile(64, 64, base, 51)
    slab, edge = mix('tan', 'stone_lt', .55), mix('tan', 'ltbrown', .45)
    for x, y in t.spots(16, .8):                       # flagstones set into packed earth
        w, h = 6 + t.ri(4), 3 + t.ri(3)
        for j in range(h):
            for i in range(w):
                if (i in (0, w - 1)) and (j in (0, h - 1)): continue
                t.set(x + i, y + j, slab)
        for i in range(1, w - 1): t.set(x + i, y + h, edge)
    for x, y in t.spots(5, .2): t.set(x, y, mix('tan', 'ltbrown', .3))
    for x, y in t.spots(6, .2): t.set(x, y, mix('sand', 'parch', .3))
    return t.im

def t_rus():
    base = mix('sand', 'ochre', .38)
    t = Tile(64, 64, base, 61)
    furrow, ridge = mix('sand', 'ltbrown', .42), mix('sand', 'parch', .20)
    for y in range(1, 64, 4):                          # ploughed furrows, broken so they stay calm
        x = 0
        while x < 64:
            run = 5 + t.ri(9)
            for i in range(run):
                if x + i < 64:
                    t.set(x + i, y, furrow)
                    if t.rnd() < .15: t.set(x + i, y - 1, ridge)
            x += run + 1 + t.ri(3)
    for x, y in t.spots(8, .35): t.set(x, (y // 4) * 4 + 3, mix('sage', 'sand', .35))
    return t.im

def t_silva():
    base = mix('olive_dk', 'forest', .22)
    t = Tile(64, 64, base, 71)
    for x, y in t.spots(4, .28): t.set(x, y, mix('forest', 'ink', .30))
    for x, y in t.spots(5, .30): t.stamp(x, y, [(0, 0, mix('olive_dk', 'olive', .45)), (1, 0, mix('olive_dk', 'olive', .45))])
    for x, y in t.spots(8, .40): t.set(x, y, mix('brown', 'olive_dk', .35))
    for x, y in t.spots(13, .5): t.stamp(x, y, [(0, 0, mix('olive', 'sage', .2)), (1, -1, mix('olive', 'sage', .2)), (-1, -1, mix('olive_dk', 'olive', .6))])
    return t.im

def t_castra():
    base = mix('ltbrown', 'tan', .62)
    t = Tile(64, 64, base, 81)
    dark, light = mix('ltbrown', 'brown', .22), mix('tan', 'sand', .45)
    for x, y in t.spots(6, .42):
        n = 2 + t.ri(3)
        for i in range(n): t.set(x + i, y, dark)
    for x, y in t.spots(5, .25): t.set(x, y, light)
    for x, y in t.spots(13, .35): t.stamp(x, y, [(0, 0, mix('stone', 'tan', .4)), (1, 0, mix('stone_lt', 'tan', .4))])
    return t.im

def slabs(size, a, b, joint, seed, w=64):
    t = Tile(w, w, a, seed)
    for y in range(w):
        for x in range(w):
            t.set(x, y, a if ((x // size) + (y // size)) % 2 == 0 else b)
            if x % size == 0 or y % size == 0: t.set(x, y, joint)
    return t

def t_templa():
    t = slabs(32, rgb('marble'), mix('marble', 'white', .40), mix('marble', 'stone_lt', .65), 91)
    vein = mix('marble', 'stone_lt', .32)
    for x, y in t.spots(16, .7):                       # faint veining
        for i in range(5 + t.ri(7)):
            if (x + i) % 32 and (y + i // 2) % 32: t.set(x + i, y + i // 2, vein)
    for x, y in t.spots(7, .25):
        if x % 32 and y % 32: t.set(x, y, rgb('white'))
    return t.im

def bond(cw, ch, tones, joint, seed, hi=None):
    """running-bond paving: cw x ch stones, every other course shifted half a stone"""
    t = Tile(64, 64, tones[0], seed)
    tone = {}
    for y in range(64):
        for x in range(64):
            row = y // ch; xs = (x + (cw // 2 if row % 2 else 0)) % 64
            key = (xs // cw, row)
            if key not in tone: tone[key] = t.pick(tones)
            c = tone[key]
            if xs % cw == 0 or y % ch == 0: c = joint
            elif hi and xs % cw == 1 and y % ch == 1: c = hi
            t.set(x, y, c)
    return t

def t_ludus():
    b = mix('stone_lt', 'marble', .30)
    t = bond(16, 8, [b, b, mix('stone_lt', 'marble', .10), mix('stone_lt', 'marble', .50)], mix('stone_lt', 'stone', .50), 101)
    for x, y in t.spots(9, .3):
        if x % 8 and y % 8: t.set(x, y, mix('stone_lt', 'stone', .25))
    return t.im

def t_urbs():
    b = mix('stone_dk', 'stone', .60)
    t = bond(8, 8, [b, b, mix('stone_dk', 'stone', .42), mix('stone_dk', 'stone', .78)], mix('stone_dk', 'ink', .22), 111,
             hi=mix('stone', 'stone_lt', .15))
    return t.im

def t_mare():
    t = Tile(64, 64, rgb('sea'), 121)
    crest, lite, trough = mix('sea', 'sea_lt', .50), mix('sea', 'sea_lt', .85), mix('sea', 'sea_dk', .40)
    for x, y in t.spots(8, .62):
        n = 3 + t.ri(3)
        for i in range(n): t.set(x + i, y, crest)
        t.set(x + 1, y, lite)
        for i in range(2): t.set(x + n - 1 + i, y + 1, trough)
    for x, y in t.spots(7, .22): t.set(x, y, trough)
    return t.im

def t_creta():
    t = Tile(64, 64, mix('ochre', 'sand', .52), 131)
    for x, y in t.spots(5, .30): t.set(x, y, mix('ochre', 'ltbrown', .30))
    for x, y in t.spots(5, .26): t.set(x, y, mix('sand', 'parch', .35))
    for x, y in t.spots(16, .6):                       # hairline cracks in baked earth
        for i in range(3 + t.ri(4)): t.set(x + i, y + (i // 2), mix('ochre', 'ltbrown', .45))
    return t.im

def t_caelum():
    t = Tile(64, 64, rgb('sky'), 141)
    c1, c2 = mix('sky', 'white', .38), mix('sky', 'white', .65)
    for x, y in t.spots(21, .9):                       # thin cloud wisps
        w = 9 + t.ri(8)
        for i in range(w): t.set(x + i, y, c1)
        for i in range(2, w - 3): t.set(x + i, y - 1, c2)
        for i in range(4, w - 1): t.set(x + i, y + 1, c1)
    for x, y in t.spots(6, .2): t.set(x, y, mix('sky', 'sea_lt', .16))
    return t.im

def t_triclinium():
    t = Tile(64, 64, rgb('terra_dk'), 151)
    tones = [mix('terra_dk', 'wine', .30), mix('terra_dk', 'wine', .30), mix('terra_dk', 'terra', .14), mix('terra_dk', 'wine', .55)]
    line, dot = mix('wine', 'ink', .25), mix('terra', 'sand', .30)
    for j in range(32):
        for i in range(32):                            # 2x2 tesserae on a diamond lattice
            c = t.pick(tones)
            if (i + j) % 8 == 0 or (i - j) % 8 == 0: c = line
            if (i % 8, j % 8) in ((4, 0), (0, 4)): c = dot
            for dy in (0, 1):
                for dx in (0, 1): t.set(i * 2 + dx, j * 2 + dy, c)
    return t.im

def t_theatrum():
    t = Tile(64, 64, mix('sand', 'parch', .32), 161)
    for x, y in t.spots(4, .26): t.set(x, y, mix('sand', 'tan', .40))
    for x, y in t.spots(5, .22): t.set(x, y, mix('parch', 'cream', .5))
    for x, y in t.spots(12, .5):                       # rake marks
        for i in range(4 + t.ri(4)): t.set(x + i, y, mix('sand', 'tan', .28))
    return t.im

def t_forum():
    t = slabs(32, mix('marble', 'cream', .50), mix('white', 'cream', .30), mix('marble', 'tan', .32), 171)
    for x, y in t.spots(8, .22):
        if x % 32 and y % 32: t.set(x, y, rgb('white'))
    for cy in (0, 32):
        for cx in (0, 32):                             # gilt inlay where four slabs meet
            for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 1)): t.set(cx + dx, cy + dy, rgb('ochre'))
            t.set(cx, cy, rgb('gold'))
    return t.im

def t_road():
    """polygonal basalt paving: a wrapped Voronoi diagram over a jittered grid of stones"""
    W = 32
    t = Tile(W, W, rgb('stone'), 7)
    seeds = []
    for gy in range(4):
        for gx in range(4):
            seeds.append((gx * 8 + (4 if gy % 2 else 0) + 1 + t.ri(6), gy * 8 + 1 + t.ri(6)))
    tones = [rgb('stone'), mix('stone', 'stone_lt', .28), mix('stone', 'stone_dk', .20), mix('stone', 'tan', .16), mix('stone', 'stone_lt', .12)]
    tone = [tones[(i * 3 + i // 4) % len(tones)] for i in range(len(seeds))]
    joint = mix('stone_dk', 'ink', .40)
    def near(x, y):
        ds = []
        for i, (sx, sy) in enumerate(seeds):
            dx = min(abs(x - sx), W - abs(x - sx)); dy = min(abs(y - sy), W - abs(y - sy))
            ds.append((math.hypot(dx, dy), i))
        ds.sort()
        return ds[0][1], ds[1][0] - ds[0][0]
    cell = {}
    for y in range(W):
        for x in range(W): cell[x, y] = near(x, y)
    isj = lambda x, y: cell[x % W, y % W][1] < 1.05
    for y in range(W):
        for x in range(W):
            i, _ = cell[x, y]
            c = tone[i]
            if isj(x, y): c = joint
            elif isj(x - 1, y) or isj(x, y - 1): c = tuple(min(255, v + 22) for v in c[:3]) + (255,)   # lit upper-left edge
            elif isj(x + 1, y) or isj(x, y + 1): c = tuple(max(0, v - 14) for v in c[:3]) + (255,)
            t.set(x, y, c)
    return t.im

def build_tiles():
    asset('tile_via', t_road(), w=32, h=32, frames=1)
    for name, fn in [('provinciae', t_provinciae), ('villa', t_villa), ('hortus', t_hortus), ('via', t_via),
                     ('taberna', t_taberna), ('rus', t_rus), ('silva', t_silva), ('castra', t_castra),
                     ('templa', t_templa), ('ludus', t_ludus), ('mare', t_mare), ('urbs', t_urbs),
                     ('creta', t_creta), ('caelum', t_caelum), ('triclinium', t_triclinium),
                     ('theatrum', t_theatrum), ('forum', t_forum)]:
        asset('bg_' + name, fn(), w=64, h=64, frames=1)
BUILDERS.append(build_tiles)

# ================================================================== PROPS
def GP(text, name='?', remap=None):
    """like G, but rows may omit trailing transparent pixels"""
    rows = rows_of(text); w = max(len(r) for r in rows)
    return G('\n'.join(r.ljust(w, '.') for r in rows), name, remap)

def prop(aid, text, remap=None):
    im = GP(text, aid, remap)
    return asset(aid, im, w=im.size[0], h=im.size[1], frames=1)

CYPRESS = """
......kk
.....kvGk
.....kvGk
....kevGGk
....kevGGk
....kevvGk
...kevvGGZk
...kevvGGZk
...kevGvGZk
...keevGGZk
..kevvvGGGZk
..kevvGvGGZk
..kevvvGGGZk
..keevvGvGZk
..kevvvGGGZk
..kevvGvGGZk
.kevvvvGGGGZk
.kevvvGvGGGZk
.keevvvGGvGZk
.kevvvvGGGGZk
.kevvGvvGGGZk
.kevvvvGvGGZk
.keevvvGGGGZk
.kevvvGvGGGZk
.kevvvvGGvGZk
.kevvvGvGvGZk
..kevvvGGGZk
..kevvGvGGZk
..kevvvGGGZk
...kvvvGGZk
....kvGGZk
.....kGZk
.....kbBk
.....kbBk
....kkbBkk
.....kkkk.....
"""
PINE = """
..........kkkkkkkk
.......kkkeeveevvGkkk
.....kkeevevvevvGvGGGkk
...kkeevvevvvGvvGvGGvGGkkk
..keevevvvGvvevvGGvGGGvGGGkk
.keevvvGvvvvGvvGvGGGvGGGGGGZk
.kevvGvvvevvGGvvGGvGGGGvGGGZk
kevvvvGvvvGGvvGGGvGGGGGGGZGZZk
kvvGvvvGGvvGGGvGGGGvGGGZGGZZZk
.kGvGGvGGGGvGGGGZGGGZGGZZZZZk
..kkGGGZGGGZGGZZGGZZZZZZZkkk
....kkkZZZkkZZZkkkZZZkkkk
......kBkkkkbBkk.kBkk
.......kBk.kbBk.kBk
........kBkkbBkkBk
.........kBbbBBk
..........kbbBk
...........kbBk
...........kbBk
...........kbBBk
...........kbBBk
............kbBk
............kbBk
............kbBk
...........kbBBk
...........kbBBk
...........kbBk
...........kbBk
...........kbBk
..........kkbBkk
..........kkkkkk..............
"""
OLIVE = """
.........kkkkkk
......kkkffefeekkk
....kkfefeefevefevkk
...kfeefefeevefevevvk
..kfefeevefevevvevvevk
.kfeefevefevevevvevvGvk
.kefevefevevvevvevvGvGk
kfevefevevvevvevvGvvGvGk
kefevevvevvevvGvvGvGvGGk
kevevvevvGvvGvvGvGvGGvGk
.kvevvGvvevvGvGvGGvGGGk
.kvvGvvGvGvGGvGvGGGGGk
..kkvGvGGvGvGGGGvGGkk
....kkGGvGGGGkGGkkk
......kkkBBkkBkk
........kbBBbk
.........kbBk
.........kbBBk
........kbBBk
........kbbBk
.......kbBbBBk
......kkbBBBBkk
......kkkkkkkkk.........
"""
BUSH = """
....kkkkk
..kkvevvGkk
.kvexevvoGGk
kvevvevGxGvGk
kevvoevvGGvGGk
kvvexvGvGvoGZk
kGvvGvGGvGxGZk
.kGGvGGZGGGZk
..kkZZGZZZkk
....kkkkkk
"""
STATUE = """
.....kkkk
....kwmmMk
....kwmMMk
....kmmMSk
.....kmMk
...kkwmmMkk
..kwmwmmmMSk
..kwmmwmMMSk
.kwmkmmwMMSk
.kmkkwmmwMSk
.kkkwmmmMwSk
...kwmmMmMSk
...kwmMmmMSk
...kwmmMmMSk
...kwmMmMMSk
...kwmmMmMSk
...kwmMmmMSk
...kwmmMmMSk
...kwmMmMMSk
..kkmmSkkMSkk
.kkkkkkkkkkkk
.kmmmmmmmmmSk
..kMMMMMMMSk
..kwmmmmmMSk
..kwmmmmmMSk
..kwmmmmmMSk
..kwmmmmmMSk
..kwmmmmmMSk
..kMMMMMMMSk
.kwmmmmmmmMSk
.kkkkkkkkkkkk.
"""
SHEEP = """
....kkkkkkkk
..kkcwwcwwcpk
kkkcwcwwcwcwpk
kBBkwwcwwcwpnk
kBkkcwwcwwcpnk
.kkkwcwwcwcpnk
...kpcwcwcppnk
...kknppnpnnk
....kBkkkkBk
....kBk..kBk
....kkk..kkk..
"""
ROCK = """
....kkkkk
..kkSmmSSkk
.kSmmSSSsSsk
kSmSSSssSsssk
kSSSsSsssssDk
kSssssssDsDDk
ksssDssDDDDDk
.kDDsDDDDDDk
..kkkkkkkkk..
"""
VINE = """
....kk
...kvekk
..kvevvek
.kevvGvvek
.kvGvkbkvGk
..kkPkbkvvk
.kPWPkbkkk
.kWPWkbkPk
..kPkkbkWPk
..kkkbBkPWk
....kbBkkPk
....kbBk.k
....kbBk
....kbBk
....kbBk
....kbBk
....kbBk
...kkbBkk
...kkkkkk...
"""
WHEAT = """
..k..kk..k
.kgkkggkkgk
kgygkgykgygk
kygykgykgygk
.kygygygygk
.kkyyyyyykk
..kylyylyk
...kxxxxk
..kylyylyk
.kyylyylyyk
.kylyylyylk
.kkkkkkkkkk.
"""
BOAT = """
.................kk
.................kBk
.......kkkkkkkkkkkBkkkkkkkkkkk
.......kbbbbbbbbbbBbbbbbbbbbbk
.......kcccccccccpBcccccccccpk
.......kcccccccccpccccccccccpk
.......kcccpccccccccccpcccccpnk
......kccccpccccccccccpcccccppnk
......kccccpccccccccccpcccccppnk
......kxxxxxxxxxxxxxxxxxxxxxxxxk
......kccccpccccccccccpcccccppnk
......kccccpccccccccccpcccccppnk
......kcccpccccccccccpcccccppnnk
.......kccpccccccccccpccccppnnk
.......kpppppppppppppppppnnnnk
.......kkkkkkkkkkkBkkkkkkkkkkk
..kk..............kBk
.kbBk.............kBk
.kbBk.............kBk.........kk
..kbBk............kBk........klk
..kbbBkkkkkkkkkkkkkBkkkkkkkkkklBk
..kllltlllllltlllllllltllllllbBk
...kbbbbbbbbbbbbbbbbbbbbbbbbbBBk
...kbBbbbbBbbbbbBbbbbbBbbbbbBBk
....kBBBBBBBBBBBBBBBBBBBBBBBBk
.....kkBBBBBBBBBBBBBBBBBBBkkk
..AFA..kkkkkkkkkkkkkkkkkkk..AFA
.AAFFFAAAFFAAAAFFFAAAAFFAAAFFFAA.
"""
WAVE = """
....FFF
..FFAAAFF..FF
.FAA...AAFFAAF
AA.......AA...
"""
STANDARD = """
..kk..kk
.kgEkkgEk
kgEggEggEk
.kkgEEgkk
...kggk
..kkyykk
.kxxxxxxk
.kxrrrrxk
.kxrggrxk
.kxrggrxk
.kxrrrrxk
.kgygygyk
..k.kk.k
....klk
...kgEgk
...kgygk
....klk
...kgEgk
...kgygk
....klk
....klk
....klk
....klk
....klk
....klk
....klk
....klk
....klk
...kklkk
...kkkkk..
"""
AMPHORA = """
...kkkk
...krok
..kkrRkk
.kokrRkRk
.kokorkRk
.kkoorRkk
.koorrrRk
kooorrrRRk
koorrrrRRk
koorrrrRRk
.korrrrRk
.korrrRRk
..korrRk
..kkrRkk
...krRk
...kkkk...
"""
BENCH = """
.....kkkkkkkk
.....kbDDbDDbk
.....kbDDbDDbk
kkkkkkkkkkkkkkkkkkkk
kltllllltlllllltlBBk
kbbbbbbbbbbbbbbbbBBk
.kkkkkkkkkkkkkkkkkk
.kbBk..........kbBk
.kbBk..........kbBk
.kbBkkkkkkkkkkkkbBk
.kbBk..........kbBk
.kkkk..........kkkk.
"""
CLOUD = """
.........wwwww
......wwwwwwwwww....www
....wwwwwwwwwwwwwwwwwwwww
..wwwwwwwwwwwwwwwwwwwwwwwww
.wwwwwwwwwFwwwwwwwwwFwwwwwww
wwwwFwwwwFFFwwwwFwwFFFwwwwFw
wFFFFFwFFFFFFFwFFFFFFFFwFFFF
.FFFFFFFFFFFFFFFFFFFFFFFFFF
..AAFFFFAAAFFFFFAAAAFFFAAA..
"""
FEATHER = """
.......kk
......kwwk
.....kwwFk
....kwwFk
...kwwFFk
..kwwFwk
..kwFwFk
.kwFwFk
.kFwFk
.kkFk
.kBk
kBk.......
"""
COUCH = """
.kkkk
kyglk
kygBkkkkkkk
kyBkcwwcpkkkkkkkkkkkkkkkkkkk
kyBkcccppkoooooooooooooooorRk
kyBkkpppkorrrrrrrrrrrrrrrrrRk
kyBkkkkkkrrrrgrrrrrgrrrrrgrRk
kylllllllllllllllllllllllllBk
kbbbbbbbbbbbbbbbbbbbbbbbbbbBk
.kkkkkkkkkkkkkkkkkkkkkkkkkkk
.klBk....................klBk
..kBk....................kBk
.klBk....................klBk
.kyBk....................kyBk
.kkkk....................kkkk.
"""
LAMP = """
...kk
..kEgk
..kgok
.kkkkkk
kzyyyyzk
.kzyyzk
..kkkk
...kzk
...kyk
...kzk
...kzk
..kzyzk
...kzk
...kzk
...kyk
...kzk
...kzk
...kzk
..kzyzk
.kzkkkzk
kzk..kzk
kkk..kkk
"""
MASK = """
...kkkkkk
.kkbBbbBbkk
kbBkkkkkkBbk
kBkoooooorkk
kbkoKKooKKrk
kbkoKKooKKrk
kBkoooorrork
kbkorKKKKrrk
kbkoKKKKKKrk
.kkorKKKKrkk
..kkrrrrrkk
....kkkkk
....kSsDk
....kSsDk
....kSsDk
...kkSsDkk
...kSSssDk
...kkkkkkk..
"""

def column_text(shaft_rows):
    cap = "kkkkkkkkkk\nkwmmmmmmSk\n.kwmmmmSk\n"
    base = ".kwmmmMSk\nkwmmmmmMSk\nkkkkkkkkkk"
    return cap + "..kwmMSk\n" * shaft_rows + base

class Cv:
    """a character canvas for sprites assembled from parts"""
    def __init__(s, w, h):
        s.w, s.h = w, h; s.g = [['.'] * w for _ in range(h)]
    def set(s, x, y, c):
        if 0 <= x < s.w and 0 <= y < s.h: s.g[y][x] = c
    def get(s, x, y):
        return s.g[y][x] if 0 <= x < s.w and 0 <= y < s.h else '.'
    def rect(s, x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1): s.set(x, y, c)
    def hline(s, x0, x1, y, c): s.rect(x0, y, x1, y, c)
    def vline(s, x, y0, y1, c): s.rect(x, y0, x, y1, c)
    def grid(s, x, y, text):
        for j, row in enumerate(rows_of(text)):
            for i, c in enumerate(row):
                if c != '.': s.set(x + i, y + j, c)
    def outline(s, c='k'):
        add = [(x, y) for y in range(s.h) for x in range(s.w) if s.g[y][x] == '.' and
               any(s.get(x + dx, y + dy) != '.' for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))]
        for x, y in add: s.g[y][x] = c
    def img(s, name='?'):
        return G('\n'.join(''.join(r) for r in s.g), name)

ROOF = ["Roor", "Roor", "Rorr", "RRRR"]          # one terracotta pan-and-cover tile
def tiled_roof(cv, x0, x1, y0, y1, inset):
    n = y1 - y0
    for y in range(y0, y1 + 1):
        d = round(inset * (y1 - y) / n)
        for x in range(x0 + d, x1 - d + 1):
            c = ROOF[(y - y0) % 4][x % 4]
            if x > x1 - d - 5: c = {'o': 'r', 'r': 'R'}.get(c, c)       # shaded right end
            cv.set(x, y, c)
        cv.set(x0 + d, y, 'k'); cv.set(x1 - d, y, 'k')
    d = inset
    cv.hline(x0 + d, x1 - d, y0, 'k'); cv.hline(x0 + d + 1, x1 - d - 1, y0 + 1, 'o')
    for x in range(x0, x1 + 1): cv.set(x, y1, 'k' if x % 4 in (0, 3) else 'R')

def house():
    cv = Cv(44, 36)
    cv.rect(2, 13, 41, 35, 'k'); cv.rect(3, 14, 40, 34, 'c'); cv.rect(36, 14, 40, 34, 'p')
    cv.hline(3, 40, 14, 'n'); cv.hline(3, 40, 15, 'p')
    cv.rect(3, 28, 40, 34, 'r'); cv.hline(3, 40, 28, 'o'); cv.rect(36, 29, 40, 34, 'R'); cv.hline(3, 40, 34, 'R')
    cv.rect(16, 17, 27, 34, 'k'); cv.rect(17, 18, 26, 34, 'B'); cv.rect(18, 19, 25, 34, 'b')     # door
    cv.vline(18, 19, 34, 'l'); cv.vline(21, 19, 34, 'B'); cv.vline(22, 19, 34, 'l'); cv.set(24, 27, 'g'); cv.set(19, 27, 'g')
    cv.hline(18, 25, 25, 'B')
    for wx in (6, 33):                                                                         # windows
        cv.rect(wx, 19, wx + 5, 23, 'k'); cv.rect(wx + 1, 20, wx + 4, 22, 'B')
        cv.vline(wx + 2, 20, 22, 'l'); cv.hline(wx - 1, wx + 6, 24, 't')
    tiled_roof(cv, 0, 43, 0, 13, 5)
    return cv.img('house')

def shop():
    cv = Cv(44, 34)
    cv.rect(2, 7, 41, 33, 'k'); cv.rect(3, 8, 40, 32, 'c'); cv.rect(37, 8, 40, 32, 'p')
    cv.rect(6, 15, 37, 27, 'k'); cv.rect(7, 16, 36, 26, 'B')                                   # dark shop opening
    cv.hline(7, 36, 21, 'b'); cv.hline(7, 36, 22, 'k')                                         # shelf
    for x in (9, 14, 19, 24, 29, 34):                                                          # jars on the shelf
        cv.rect(x, 18, x + 1, 20, 'r'); cv.set(x, 18, 'o'); cv.set(x, 17, 'R'); cv.set(x + 1, 17, 'R')
    cv.rect(4, 27, 39, 33, 'k'); cv.hline(5, 38, 27, 'm'); cv.rect(5, 28, 38, 32, 'S'); cv.rect(35, 28, 38, 32, 's')   # counter
    for x0, c, c2 in ((8, 'o', 'r'), (17, 'A', 'a'), (26, 'y', 'z')):                          # marble inlay panels
        cv.rect(x0, 29, x0 + 6, 31, c); cv.hline(x0, x0 + 6, 31, c2)
    cv.grid(9, 23, ".kk.\nkynk\nkyyk")                                                         # loaves and a jug on the counter
    cv.grid(14, 23, ".kk.\nkynk\nkyyk")
    cv.grid(29, 21, ".kk.\n.kok\nkork\nkrRk\nkrRk")
    for y in range(8, 15):                                                                     # striped awning
        for x in range(3, 41):
            red = ((x - 3) // 4) % 2 == 0
            c = ('x' if red else 'c') if y < 13 else ('W' if red else 'n')
            if y == 8: c = 'o' if red else 'w'
            cv.set(x, y, c)
    for x in range(3, 41): cv.set(x, 15, 'k' if (x - 3) % 4 in (0, 3) else ('W' if ((x - 3) // 4) % 2 == 0 else 'n'))
    for x in range(3, 41):
        if (x - 3) % 4 in (1, 2): cv.set(x, 16, 'k')
    cv.vline(2, 8, 15, 'k'); cv.vline(41, 8, 15, 'k')
    tiled_roof(cv, 0, 43, 0, 7, 3)
    return cv.img('shop')

COL6 = "kwmMSk"                                       # one row of a fluted marble shaft
def temple_column(cv, x, y0, y1):
    cv.grid(x - 1, y0, "kkkkkkkk\nkwmmmMSk")
    for y in range(y0 + 2, y1 - 1): cv.grid(x, y, COL6)
    cv.grid(x - 1, y1 - 1, "kwmmmMSk\nkkkkkkkk")

def pediment(cv, cx2, y0, y1, half0, half1, field, rim='m'):
    """triangular gable: cx2 is twice the centre x (so it can sit between two pixels)"""
    n = y1 - y0
    for y in range(y0, y1 + 1):
        half = round(half0 + (half1 - half0) * (y - y0) / n)
        xa, xb = (cx2 + 1) // 2 - half, cx2 // 2 + half
        for x in range(xa, xb + 1):
            e = min(x - xa, xb - x)
            cv.set(x, y, 'k' if e == 0 else 'w' if e == 1 else rim if e == 2 else 'S' if e == 3 else field)
    cv.hline((cx2 + 1) // 2 - half1, cx2 // 2 + half1, y1, 'k')

def steps(cv, x0, x1, y0, n, grow=2):
    for i in range(n):
        a, b, y = x0 - i * grow, x1 + i * grow, y0 + i * 2
        cv.hline(a, b, y, 'm'); cv.hline(a, b, y + 1, 'S'); cv.set(a, y, 'k'); cv.set(b, y, 'k'); cv.set(a, y + 1, 'k'); cv.set(b, y + 1, 'k')
        cv.hline(b - 3, b - 1, y, 'M')
    cv.hline(x0 - (n - 1) * grow, x1 + (n - 1) * grow, y0 + n * 2 - 1, 'k')

def templum():
    cv = Cv(48, 46)
    cv.rect(5, 17, 42, 39, 'k'); cv.rect(6, 18, 41, 39, 'S'); cv.hline(6, 41, 18, 's'); cv.hline(6, 41, 19, 's')   # cella in shade
    cv.rect(19, 23, 28, 39, 'k'); cv.rect(20, 24, 27, 39, 'z'); cv.vline(23, 24, 39, 'B'); cv.vline(24, 24, 39, 'y')
    for y in (27, 33): cv.set(21, y, 'g'); cv.set(26, y, 'g')
    for x in (6, 16, 26, 36): temple_column(cv, x, 18, 39)
    cv.rect(3, 12, 44, 17, 'k'); cv.hline(4, 43, 13, 'w'); cv.hline(4, 43, 14, 'm'); cv.hline(4, 43, 15, 'M'); cv.hline(4, 43, 16, 'S')
    for x in range(6, 43, 4): cv.set(x, 15, 'S')
    pediment(cv, 47, 1, 12, 2, 23, 'M')
    cv.grid(22, 7, ".gg.\ngEEg\ngEgy\n.yy.")
    cv.grid(22, 0, ".gg.\ngEgy")
    steps(cv, 4, 43, 40, 3)
    return cv.img('templum')

def wall():
    cv = Cv(32, 18)
    for x in range(1, 31):
        top = 1 if (x - 1) % 8 < 5 else 5
        for y in range(top, 17):
            c = 's'
            if (y - 1) % 4 == 0: c = 'D' if y > 5 else 'S'
            elif (x + (4 if ((y - 1) // 4) % 2 else 0)) % 8 == 0 and y > 5: c = 'D'
            elif (y - 1) % 4 == 1: c = 'S'
            if x > 26 and c != 'D': c = 'D' if c == 's' else 's'
            cv.set(x, y, c)
    cv.outline()
    return cv.img('wall')

def labyrinth():
    cv = Cv(24, 23)
    cv.rect(0, 0, 23, 19, 'k'); cv.rect(1, 1, 22, 18, 'S'); cv.hline(1, 22, 1, 'm'); cv.vline(1, 1, 18, 'm')
    for i, gap_bottom in enumerate((True, False, True)):
        a = 3 + i * 3; x0, y0, x1, y1 = a, a, 23 - a, 19 - a
        for x in range(x0, x1 + 1): cv.set(x, y0, 'D'); cv.set(x, y1, 'D')
        for y in range(y0, y1 + 1): cv.set(x0, y, 'D'); cv.set(x1, y, 'D')
        gy = y1 if gap_bottom else y0
        cv.set(11, gy, 'S'); cv.set(12, gy, 'S')
    cv.set(11, 9, 'x'); cv.set(12, 9, 'x'); cv.set(11, 10, 'x'); cv.set(12, 10, 'R')
    cv.rect(0, 20, 23, 22, 'k'); cv.hline(1, 22, 20, 's'); cv.hline(1, 22, 21, 'D')
    return cv.img('labyrinth')

def arena():
    W, H = 44, 24
    cv = Cv(W, H)
    cx, cy, rx, ry = 21.5, 9.0, 20.5, 8.0
    def rho(x, y, dy=0): return math.hypot((x - cx) / rx, (y - dy - cy) / ry)
    for y in range(H):
        for x in range(W):
            r = rho(x, y)
            if r <= 1:
                if r < .46: c = 'n' if (x + y * 3) % 7 else 'p'
                elif r < .54: c = 'k'
                elif r < .64: c = 't'
                elif r < .76: c = 'p'
                elif r < .86: c = 'n'
                elif r < .94: c = 'p'
                else: c = 'c'
                if x > 30 and c in 'pn': c = {'p': 'n', 'n': 't'}[c]
                cv.set(x, y, c)
            else:
                d = next((k for k in range(1, 8) if rho(x, y, k) <= 1), None)   # facade below the rim
                if d and y > cy:
                    c = 'c' if d == 1 else 't' if d == 7 else 'p'
                    if 3 <= d <= 5 and x % 4 in (1, 2): c = 'B'
                    if d == 2 and x % 4 in (1, 2): c = 'n'
                    if x > 30 and c == 'p': c = 'n'
                    cv.set(x, y, c)
    cv.outline()
    return cv.img('arena')

def tent():
    """legionary hide tent, gable end on: a pale goatskin A-frame with a dark doorway and a red pennant"""
    cv = Cv(36, 23)
    for r in range(18):
        y = 4 + r; xa, xb = 17 - r, 18 + r
        for x in range(xa, xb + 1):
            c = 'n' if x <= 17 else 't'
            if x == 17 - r // 2: c = 'p'                        # lit seam
            if x == 18 + r // 2: c = 'l'                        # shaded seam
            if x >= xb - 2 and r > 3: c = 'l'
            if r >= 7:                                          # doorway
                hw = (r - 7) // 3 + 1
                if 18 - hw <= x <= 17 + hw: c = 'K' if abs(x - 17.5) < hw else 'k'
            cv.set(x, y, c)
        cv.set(xa, y, 'k'); cv.set(xb, y, 'k')
    cv.hline(0, 35, 22, 'k'); cv.hline(16, 19, 3, 'k')
    cv.grid(17, 0, "kxxk\nkxxxk\nkkk.")
    return cv.img('tent')

def build_props():
    for aid, text in [('prop_cypress', CYPRESS), ('prop_pine', PINE), ('prop_olive', OLIVE), ('prop_bush', BUSH),
                      ('prop_statue', STATUE), ('prop_sheep', SHEEP), ('prop_rock', ROCK), ('prop_vine', VINE),
                      ('prop_wheat', WHEAT), ('prop_boat', BOAT), ('prop_wave', WAVE),
                      ('prop_standard', STANDARD), ('prop_amphora', AMPHORA), ('prop_bench', BENCH),
                      ('prop_cloud', CLOUD), ('prop_feather', FEATHER), ('prop_couch', COUCH), ('prop_lamp', LAMP),
                      ('prop_mask', MASK)]:
        prop(aid, text)
    prop('prop_column', column_text(22))
    for aid, fn in [('prop_tent', tent), ('prop_house', house), ('prop_shop', shop), ('prop_templum', templum), ('prop_wall', wall),
                    ('prop_labyrinth', labyrinth), ('prop_arena', arena)]:
        im = fn(); asset(aid, im, w=im.size[0], h=im.size[1], frames=1)
BUILDERS.append(build_props)

# ================================================================== CITY
# Buildings and street life for the districts that lie inside Rome. In assets.json a district
# with a `buildings` list is laid out as a city: rows of these shoulder to shoulder, with the
# district's `props` (people, carts, lamps) on the pavement. Monuments also appear as props.
def window(cv, x, y, w=4, h=6, sill='t', shutter=None):
    cv.rect(x, y, x + w - 1, y + h - 1, 'k'); cv.rect(x + 1, y + 1, x + w - 2, y + h - 2, 'B')
    if shutter: cv.vline(x + 1, y + 1, y + h - 2, shutter)
    if sill: cv.hline(x - 1, x + w, y + h, sill)

def arched(cv, x0, x1, ytop, ybot, fill='B', frame='k'):
    """round-headed opening from x0 to x1 with its crown at ytop"""
    def shape(a, b, top, c):
        r = (b - a + 1) / 2; cx = (a + b) / 2
        for y in range(top, ybot + 1):
            for x in range(a, b + 1):
                if y < top + r and (x - cx) ** 2 + (top + r - y - .5) ** 2 > r * r: continue
                cv.set(x, y, c)
    if frame: shape(x0 - 1, x1 + 1, ytop - 1, frame)
    shape(x0, x1, ytop, fill)

def insula():
    """apartment block (insula): shops at street level, a timber balcony, three floors of small windows"""
    W, H = 42, 60
    cv = Cv(W, H)
    cv.rect(2, 7, 39, 59, 'k'); cv.rect(3, 8, 38, 58, 'c'); cv.rect(34, 8, 38, 58, 'p')
    cv.hline(3, 38, 8, 'n'); cv.hline(3, 38, 9, 'p')
    for y in (21, 33): cv.hline(3, 38, y, 'n')                                    # string courses
    for fy in (11, 23):                                                           # two floors of windows
        for i, wx in enumerate((6, 14, 24, 32)):
            window(cv, wx, fy, 4, 6, shutter='l' if (i + fy) % 3 == 0 else None)
    cv.grid(23, 30, "wAwwx\nw.w.x")                                               # washing hung out to dry
    for wx in (7, 19, 31): cv.rect(wx, 35, wx + 3, 42, 'k'); cv.rect(wx + 1, 36, wx + 2, 42, 'B')   # doors onto the balcony
    cv.rect(1, 40, 40, 45, 'k'); cv.hline(2, 39, 40, 'l')                         # balcony (maenianum)
    for y in (41, 42, 43):
        for x in range(2, 40): cv.set(x, y, 'k' if x % 3 == 0 else ('B' if x > 34 else 'b'))
    cv.hline(2, 39, 44, 'B')
    for x in (5, 20, 36): cv.grid(x, 46, "BB\n.B")                                # brackets
    cv.rect(3, 52, 38, 58, 'r'); cv.hline(3, 38, 52, 'o'); cv.rect(34, 53, 38, 58, 'R')             # red dado
    for a, b in ((5, 16), (25, 36)):                                              # two shops
        cv.rect(a, 47, b, 59, 'k'); cv.rect(a + 1, 50, b - 1, 58, 'B'); cv.hline(a + 1, b - 1, 48, 'l'); cv.hline(a + 1, b - 1, 49, 'b')
    for x in (7, 10, 13): cv.rect(x, 51, x + 1, 53, 'r'); cv.set(x, 51, 'o'); cv.set(x, 50, 'R')    # amphorae on a shelf
    cv.hline(6, 15, 54, 'b'); cv.hline(6, 15, 55, 'm'); cv.rect(6, 56, 15, 58, 'S'); cv.rect(13, 56, 15, 58, 's')
    cv.grid(27, 51, "o.o.o.o\nr.r.r.r")                                           # sausages on a rail
    cv.grid(27, 54, "ny.nyy\nyylyyl"); cv.hline(26, 35, 56, 'l'); cv.rect(26, 57, 35, 58, 'b')      # loaves on a table
    cv.rect(19, 48, 22, 59, 'k'); cv.rect(20, 49, 21, 58, 'b'); cv.vline(20, 49, 58, 'l')           # stair door
    tiled_roof(cv, 0, 41, 0, 7, 3)
    return cv.img('insula')

def insula_b():
    """smaller apartment block in bare brick with travertine string courses and an arched shop"""
    W, H = 34, 50
    cv = Cv(W, H)
    cv.rect(1, 6, 32, 49, 'k')
    for y in range(7, 49):
        for x in range(2, 32):
            c = 'r' if y % 3 == 0 else 'o'
            if x > 27: c = 'R' if c == 'r' else 'r'
            cv.set(x, y, c)
    cv.hline(2, 31, 7, 'R')
    for y in (21, 35): cv.hline(2, 31, y, 'm'); cv.hline(2, 31, y + 1, 'S'); cv.set(31, y, 'M')
    for fy in (10, 24):
        for wx in (5, 15, 25):
            cv.hline(wx - 1, wx + 4, fy - 1, 'R'); window(cv, wx, fy, 4, 7, sill='m')
    cv.grid(4, 29, ".v.e..\nvevvev")                                              # herbs in a window box
    arched(cv, 4, 17, 38, 49, 'B', 'k')
    for x in (7, 10, 13): cv.rect(x, 42, x + 1, 44, 'y'); cv.set(x, 42, 'n'); cv.set(x + 1, 44, 'z')
    cv.hline(5, 16, 45, 'm'); cv.rect(5, 46, 16, 48, 'S'); cv.rect(14, 46, 16, 48, 's')
    arched(cv, 22, 27, 40, 49, 'b', 'k'); cv.vline(22, 43, 48, 'l'); cv.vline(25, 41, 48, 'B')
    cv.hline(1, 32, 49, 'k')
    tiled_roof(cv, 0, 33, 0, 6, 3)
    return cv.img('insula_b')

def domus():
    """town house (domus): a blind street wall with a tall doorway, the atrium roof rising behind"""
    W, H = 54, 34
    cv = Cv(W, H)
    cv.rect(15, 6, 38, 14, 'k'); cv.rect(16, 7, 37, 14, 'p'); cv.hline(16, 37, 7, 'n')              # atrium block
    for wx in (19, 33): cv.rect(wx, 9, wx + 1, 10, 'B')
    tiled_roof(cv, 13, 40, 0, 6, 4)
    cv.rect(24, 1, 29, 3, 'k'); cv.rect(25, 2, 28, 3, 'K')                                          # the compluvium, open to the sky
    cv.rect(2, 19, 51, 33, 'k'); cv.rect(3, 20, 50, 32, 'c'); cv.rect(46, 20, 50, 32, 'p'); cv.hline(3, 50, 20, 'n')
    cv.rect(3, 27, 50, 32, 'r'); cv.hline(3, 50, 27, 'o'); cv.rect(46, 28, 50, 32, 'R')
    tiled_roof(cv, 0, 53, 12, 19, 3)
    cv.rect(20, 20, 33, 33, 'k'); cv.rect(21, 21, 32, 32, 'm'); cv.vline(32, 21, 32, 'S'); cv.vline(31, 23, 32, 'M')   # stone door case
    cv.rect(23, 23, 30, 32, 'k'); cv.rect(24, 24, 29, 32, 'b'); cv.vline(24, 24, 32, 'l'); cv.vline(26, 24, 32, 'B'); cv.vline(27, 24, 32, 'l')
    for y in (26, 30): cv.set(25, y, 'g'); cv.set(28, y, 'g')
    for wx in (7, 13, 38, 44): cv.rect(wx, 22, wx + 2, 24, 'k'); cv.set(wx + 1, 23, 'B')            # high slit windows
    cv.rect(35, 29, 42, 32, 'k'); cv.hline(36, 41, 30, 'm'); cv.hline(36, 41, 31, 'S'); cv.hline(37, 40, 32, 'R')     # stone bench
    cv.grid(13, 25, ".vev.\nvGvev\nvvGvv\n.vGv.\n..B..\n.oor.\n.orR.")                              # laurel in a tub
    return cv.img('domus')

def thermae():
    """public baths: a vaulted hall with a great lunette window, a domed hot room and a furnace flue"""
    W, H = 60, 46
    cv = Cv(W, H)
    cv.rect(1, 22, 58, 45, 'k'); cv.rect(2, 23, 57, 44, 'c'); cv.rect(52, 23, 57, 44, 'p'); cv.hline(2, 57, 23, 'n')
    for y in range(8, 23):                                                        # dome of the caldarium
        for x in range(1, 19):
            r = math.hypot((x - 9.5) / 8.6, (y - 22.5) / 13.5)
            if r <= 1: cv.set(x, y, 'k' if r > .89 else 'w' if (x - 6) ** 2 + (y - 14) ** 2 < 5 else 'm' if x < 9 else 'M' if x < 13 else 'S')
    cv.grid(8, 7, ".kk.\nkmSk")
    tiled_roof(cv, 42, 59, 16, 22, 2)                                             # lean-to over the furnace room
    cv.rect(49, 7, 54, 17, 'k'); cv.rect(50, 8, 53, 16, 'o'); cv.vline(53, 8, 16, 'r')
    for y in (10, 13): cv.hline(50, 53, y, 'r')
    cv.grid(48, 0, "...mm.\n.mmSSm\nmSSmS.\n.mSSm.\n..SmS.\n...S..\n..mS..")           # smoke
    cv.rect(17, 8, 42, 45, 'k'); cv.rect(18, 9, 41, 44, 'c'); cv.rect(37, 9, 41, 44, 'p'); cv.hline(18, 41, 9, 'n')   # the great hall
    for y in range(13, 28):
        for x in range(18, 42):
            d = math.hypot(x - 29.5, y - 27.5)
            if d > 11.3: continue
            if d > 10.3: c = 'k'
            elif d > 8.6: c = 'o' if (x + y) % 3 else 'r'
            elif d > 7.7: c = 'k'
            else: c = 'A' if (x + y) % 7 == 0 else 'a' if (x - y) % 5 == 0 else 'N'
            cv.set(x, y, c)
    for x in (26, 33): cv.vline(x, 20, 27, 'c')                                   # mullions
    cv.hline(18, 41, 28, 'k'); cv.hline(19, 40, 29, 'm'); cv.hline(19, 40, 30, 'S')
    cv.rect(24, 32, 35, 45, 'k'); cv.rect(25, 33, 34, 44, 'm'); cv.vline(34, 33, 44, 'S')
    cv.rect(27, 35, 32, 44, 'k'); cv.rect(28, 36, 31, 44, 'z'); cv.vline(29, 36, 44, 'B'); cv.vline(30, 36, 44, 'y')
    for a in (4, 10, 45, 51): arched(cv, a, a + 3, 28, 35, 'N', 'k'); cv.set(a + 1, 30, 'a')
    cv.rect(2, 40, 23, 44, 'S'); cv.hline(2, 23, 40, 'm'); cv.rect(36, 40, 57, 44, 'S'); cv.hline(36, 57, 40, 'm'); cv.rect(52, 41, 57, 44, 's')
    tiled_roof(cv, 15, 44, 1, 8, 6)
    return cv.img('thermae')

def basilica():
    """basilica (law court and exchange): two storeys of marble arcades under a long tiled roof"""
    W, H = 68, 46
    cv = Cv(W, H)
    cv.rect(2, 8, 65, 41, 'k'); cv.rect(3, 9, 64, 41, 'm'); cv.rect(59, 9, 64, 41, 'M')
    cv.hline(3, 64, 9, 'w'); cv.hline(3, 64, 10, 'S')
    for i in range(6):
        x = 6 + i * 10
        arched(cv, x, x + 5, 13, 21, 'D', 'k'); cv.hline(x, x + 5, 21, 'k'); cv.hline(x, x + 5, 20, 's')
        arched(cv, x, x + 5, 28, 41, 'B', 'k'); cv.set(x + 2, 31, 'D'); cv.set(x + 3, 33, 'D')
    for x in (3, 13, 23, 33, 43, 53, 63):                                         # half-columns on the piers
        for y0, y1 in ((12, 21), (27, 41)):
            cv.vline(x, y0, y1, 'w'); cv.vline(x + 1, y0, y1, 'M' if x < 59 else 'S')
    cv.rect(2, 22, 65, 26, 'k'); cv.hline(3, 64, 23, 'w'); cv.hline(3, 64, 24, 'm'); cv.hline(3, 64, 25, 'M')
    for x in range(5, 64, 3): cv.set(x, 24, 'S')
    tiled_roof(cv, 0, 67, 0, 8, 5)
    steps(cv, 2, 65, 42, 2, grow=1)
    return cv.img('basilica')

MILL = """
.kkkkk.
kDssSSk
kDssSSk
.kDsSk.
bbkDkbb
.kDsSk.
kDssSSk
kDsssSk
kkkkkkk
kDDDDsk
kkkkkkk
"""
def pistrinum():
    """bakery (pistrinum): a domed brick oven with a fire in its mouth, loaves on the shelves, lava mills in the yard"""
    W, H = 42, 37
    cv = Cv(W, H)
    cv.rect(2, 7, 39, 28, 'k'); cv.rect(3, 8, 38, 27, 'c'); cv.rect(34, 8, 38, 27, 'p'); cv.hline(3, 38, 8, 'n'); cv.hline(3, 38, 9, 'p')
    for y in range(10, 28):                                                       # the oven
        for x in range(3, 22):
            d = math.hypot(x - 12, (y - 27) * .95)
            if d > 9.4: continue
            c = 'k' if d > 8.5 else ('o' if (x + y * 2) % 4 else 'r')
            if d <= 4.7: c = 'k' if d > 3.8 else 'K'
            cv.set(x, y, c)
    cv.grid(10, 24, ".gE.\ngEEg\nxgEg\nxxgx")
    cv.rect(23, 12, 36, 28, 'k'); cv.rect(24, 13, 35, 27, 'B')                     # the shop
    for sy in (16, 20):
        cv.hline(24, 35, sy, 'b')
        for x in (25, 29, 33): cv.grid(x, sy - 2, "ny\nyl")
    cv.hline(24, 35, 23, 'm'); cv.rect(24, 24, 35, 27, 'S'); cv.rect(33, 24, 35, 27, 's')
    tiled_roof(cv, 0, 41, 2, 8, 3)
    cv.rect(9, 0, 14, 5, 'k'); cv.rect(10, 1, 13, 4, 'o'); cv.vline(13, 1, 4, 'r'); cv.hline(10, 13, 3, 'r')    # chimney
    cv.grid(0, 26, MILL); cv.grid(17, 26, MILL)
    cv.grid(29, 30, ".kkkk.\nknnntk\nknnttk\nknnttk\nkntttk\n.kkkk.")                # a sack of grain
    return cv.img('pistrinum')

def tholos():
    """round temple (like Vesta's): a ring of columns under a conical roof with a gilded finial"""
    W, H = 36, 42
    cv = Cv(W, H)
    for y in range(3, 14):
        half = round(2 + (y - 3) * 1.5)
        xa, xb = 18 - half, 17 + half
        for x in range(xa, xb + 1):
            c = 'o' if x < 15 else 'r' if x < 24 else 'R'
            if any(round(17.5 + half * t) == x for t in (-.62, -.3, 0, .3, .62)): c = {'o': 'r', 'r': 'R', 'R': 'W'}[c]   # ribs down the cone
            cv.set(x, y, 'k' if x in (xa, xb) else c)
    cv.grid(16, 0, ".kk.\nkgEk\nkgyk")
    cv.rect(3, 18, 32, 35, 'S'); cv.rect(3, 18, 32, 19, 's'); cv.vline(8, 18, 35, 's'); cv.vline(27, 18, 35, 's')
    cv.rect(15, 22, 20, 35, 'k'); cv.rect(16, 23, 19, 35, 'z'); cv.vline(17, 23, 35, 'B'); cv.vline(18, 23, 35, 'y')
    for x in (2, 9, 21, 28): temple_column(cv, x, 18, 35)
    cv.rect(1, 14, 34, 17, 'k'); cv.hline(2, 33, 15, 'w'); cv.hline(2, 33, 16, 'M')
    for x in range(4, 33, 3): cv.set(x, 16, 'S')
    for i, (a, b) in enumerate(((2, 33), (1, 34), (0, 35))):
        y = 36 + i * 2
        cv.hline(a, b, y, 'm'); cv.hline(a, b, y + 1, 'S'); cv.hline(b - 3, b - 1, y, 'M')
        for yy in (y, y + 1): cv.set(a, yy, 'k'); cv.set(b, yy, 'k')
    cv.hline(0, 35, 41, 'k')
    return cv.img('tholos')

def portico():
    """a stretch of colonnade (porticus) under a tiled roof"""
    W, H = 46, 30
    cv = Cv(W, H)
    cv.rect(1, 12, 44, 27, 'k'); cv.rect(2, 13, 43, 27, 'S'); cv.rect(2, 13, 43, 15, 's')
    for x in (13, 31): cv.rect(x, 18, x + 3, 27, 'k'); cv.rect(x + 1, 19, x + 2, 27, 'D')
    for x in (2, 11, 20, 29, 38): temple_column(cv, x, 13, 27)
    cv.rect(0, 8, 45, 12, 'k'); cv.hline(1, 44, 9, 'w'); cv.hline(1, 44, 10, 'm'); cv.hline(1, 44, 11, 'S')
    tiled_roof(cv, 0, 45, 0, 7, 2)
    cv.hline(0, 45, 28, 'm'); cv.hline(40, 44, 28, 'M'); cv.set(0, 28, 'k'); cv.set(45, 28, 'k'); cv.hline(0, 45, 29, 'k')
    return cv.img('portico')

def aqueduct():
    """three arches of an aqueduct carrying its covered water channel; the ground shows through"""
    W, H = 54, 46
    cv = Cv(W, H)
    for y in range(H):
        for x in range(W):
            c = 'S'
            if y % 5 == 4: c = 's'
            elif (x + (3 if (y // 5) % 2 else 0)) % 6 == 0: c = 's'
            if x % 16 in (4, 5): c = 'D' if c == 's' else 's'                       # shaded side of each pier
            cv.set(x, y, c)
    cv.rect(0, 0, 53, 8, 'k'); cv.hline(1, 52, 1, 'm'); cv.rect(1, 2, 52, 5, 'S'); cv.hline(1, 52, 6, 's'); cv.hline(1, 52, 7, 'm')
    for x in range(4, 52, 6): cv.set(x, 3, 's'); cv.set(x, 4, 's')
    for a in (6, 22, 38): arched(cv, a, a + 9, 13, 45, '.', 'k')
    cv.vline(0, 0, 45, 'k'); cv.vline(53, 0, 45, 'k')
    for a in (0, 16, 32, 48): cv.hline(a, a + 5, 45, 'k')
    for x, y in ((2, 20), (18, 33), (35, 15), (50, 28), (19, 12)): cv.set(x, y, 'v'); cv.set(x + 1, y + 1, 'e')
    return cv.img('aqueduct')

def theatre():
    """theatre: the curved outer wall of the seating, two tiers of arcades below a plain attic"""
    W = 60
    fl = Cv(W, 40)
    fl.rect(0, 0, W - 1, 39, 'p')
    fl.hline(0, W - 1, 0, 'k'); fl.hline(0, W - 1, 1, 'c')
    for y, c in ((8, 'c'), (9, 'n'), (22, 'c'), (23, 'n'), (24, 't')): fl.hline(0, W - 1, y, c)
    x = 4
    for wdt in (4, 6, 6, 6, 6, 4):
        a, b = x, x + wdt - 1
        arched(fl, a, b, 12, 20, 'D', 'k'); fl.hline(a, b, 20, 's')
        arched(fl, a, b, 27, 39, 'B', 'k')
        fl.rect((a + b) // 2, 3, (a + b) // 2 + 1, 5, 'B')                                           # attic windows
        x = b + 5
    # half-columns on the piers
    x = 4
    for wdt in (4, 6, 6, 6, 6, 4):
        fl.vline(x - 3, 10, 21, 'c'); fl.vline(x - 3, 25, 39, 'c')
        x += wdt + 4
    fl.vline(x - 3, 10, 21, 'c'); fl.vline(x - 3, 25, 39, 'c')
    cv = Cv(W, 42)
    for x in range(W):
        drop = 2 - round(2 * (abs(x - 29.5) / 29.5) ** 2)                                            # the wall curves away at both ends
        for y in range(40):
            c = fl.get(x, y)
            if x >= 47 or x <= 1: c = {'c': 'p', 'p': 'n', 'n': 't', 't': 'l'}.get(c, c)
            elif 10 <= x <= 26: c = {'p': 'c'}.get(c, c) if y < 8 or 9 < y < 22 else c
            cv.set(x, y + drop, c)
        cv.set(x, 39 + drop, 'k' if cv.get(x, 39 + drop) != 'B' else 'K')
    for y in range(42):
        if cv.get(0, y) != '.': cv.set(0, y, 'k')
        if cv.get(W - 1, y) != '.': cv.set(W - 1, y, 'k')
    return cv.img('theatre')

def obelisk():
    """obelisk of red granite with a gilded tip, as on the spina of the Circus"""
    W, H = 12, 46
    cv = Cv(W, H)
    cv.grid(3, 0, "..kk..\n.kEgk.\n.kEgk.\nkEggyk")
    for y in range(4, 38):
        half = 2 if y < 21 else 3
        xa, xb = 6 - half, 5 + half
        cv.set(xa - 1, y, 'k'); cv.set(xb + 1, y, 'k')
        for x in range(xa, xb + 1): cv.set(x, y, 'o' if x == xa else 'R' if x == xb else 'r')
    for y in range(7, 35, 5): cv.set(5, y, 'R'); cv.set(6, y + 1, 'R'); cv.set(5, y + 2, 'o')        # hieroglyphs
    cv.rect(1, 38, 10, 45, 'k'); cv.rect(2, 39, 9, 44, 'm'); cv.vline(9, 39, 44, 'S'); cv.vline(8, 40, 44, 'M'); cv.hline(2, 9, 39, 'w')
    cv.rect(0, 43, 11, 45, 'k'); cv.hline(1, 10, 44, 'S'); cv.set(1, 44, 'm'); cv.set(2, 44, 'm')
    return cv.img('obelisk')

def columna():
    """honorary column: reliefs winding up the shaft, a gilded statue on top"""
    W, H = 16, 56
    cv = Cv(W, H)
    cv.grid(5, 0, "..kk..\n.kgEk.\n.kgyk.\nkgEgyk\nkgEgyk\n.kgyk.\n.kgyk.\n.kyyk.")
    cv.rect(3, 8, 12, 10, 'k'); cv.hline(4, 11, 9, 'm'); cv.set(11, 9, 'S'); cv.set(4, 9, 'w')
    for y in range(11, 44):
        cv.set(4, y, 'k'); cv.set(11, y, 'k')
        for x in range(5, 11):
            c = "wmmmMS"[x - 5]
            if (x + y) % 5 == 0: c = {'w': 'M', 'm': 'M', 'M': 'S', 'S': 's'}[c]
            cv.set(x, y, c)
    cv.rect(2, 44, 13, 46, 'k'); cv.hline(3, 12, 45, 'm'); cv.set(12, 45, 'S')
    cv.rect(1, 46, 14, 55, 'k'); cv.rect(2, 47, 13, 54, 'm'); cv.rect(11, 47, 13, 54, 'S'); cv.hline(2, 13, 47, 'w')
    cv.rect(6, 50, 9, 55, 'k'); cv.rect(7, 51, 8, 54, 'z')
    cv.hline(0, 15, 55, 'k')
    return cv.img('columna')

def rostra():
    """the Rostra: the speakers' platform in the Forum, its front hung with the bronze rams of captured ships"""
    W, H = 46, 22
    cv = Cv(W, H)
    cv.rect(2, 0, 43, 6, 'k'); cv.hline(3, 42, 1, 'w')
    for y in (2, 3, 4):
        for x in range(3, 43): cv.set(x, y, 'k' if x % 3 == 0 else ('M' if x > 38 else 'm'))
    cv.hline(3, 42, 5, 'M')
    cv.rect(1, 6, 44, 21, 'k'); cv.rect(2, 7, 43, 20, 'm'); cv.rect(39, 7, 43, 20, 'M'); cv.hline(2, 43, 7, 'w'); cv.rect(2, 19, 43, 20, 'S')
    for x in (5, 15, 25, 35):
        cv.rect(x - 1, 9, x + 5, 17, 'M'); cv.grid(x, 10, ".kkk.\nkgEgk\nkzgzk\nkzzzk\n.kzk.\n..k..")
    return cv.img('rostra')

ALTAR = """
.....xg
....xgEo
...kogEgxk
.kkkkkkkkkkk
.kwmmmmmmMSk
..kkkkkkkkk
..kwmmmmMSk
..kvevevemk
..kwmxmmMSk
..kwmmmmMSk
..kwmmmmMSk
.kkkkkkkkkkk
.kwmmmmmmMSk
kkkkkkkkkkkkk
kwMMMMMMMMSSk
kkkkkkkkkkkkk
"""
CIVIS = """
...kkkkkk
..kBBBBBBk
..kBhhhhBk
..khkhhkHk
..khhhhhHk
...khhhHk
.kkkkHHkkkk
.kwwwpwwcpk
.kwwpwwccpk
.kwpwhhcppk
.kpwwwccppk
.kwwwpwccpk
.kwwpwwcppk
.kwpwwcccpk
.kwwwpwccpk
.kwwpwwcppk
.kwpwwcccpk
..kwwpwcpk
..kwpwccpk
..kkhkkHkk
..kbbkkbBk
..kkkkkkkk
"""
MATRONA = """
...kkkkkk
..kWWWWWWk
.kWWBBBBWWk
.kWBhhhhBWk
.kWhkhhkhWk
.kWhhhhhHPk
.kWWhhhHWPk
.kWWWHHWWPk
.kWWAAAAWPk
.kWAAYAAAPk
.kWhAYAAaPk
.kWWAYAAaPk
..kWAAYAaPk
..kWAAYAak
..kAAAYAak
..kAAYAAak
..kAAYAAak
..kAAYAaak
..kAAAYaak
..kAAAAaak
..khhkkhHk
..kkkkkkkk
"""
MERCATOR = """
..kkkkkkkk
.kynyynyylk
.kltlttltlk
..kkkkkkkk
..kBhhhhBk
..khkhhkHk
..khhhhhHk
...khhhHk
.kkkkHHkkkk
.kttttttllk
.khtttttlHk
.khtttttlHk
.khBBBBBBHk
.khtttttlHk
.kkttttllkk
..kttttllk
..kkkkkkkk
..kHHkkHHk
..khhkkhHk
..khhkkhHk
..kbbkkbBk
..kkkkkkkk
"""
PLAUSTRUM = """
............kok.kok.kok
...........korkkorkkork
...........krRkkrRkkrRk
.....kkkkkkkrRkkrRkkrRkkk
.....klllllllllllllllllltk
.....kbbbbbbbbbbbbbbbbbbBk
....kkkkkkkkkkkkkkkkkkkkkk
...kbk.....kkkkkk
..kbk....kkblllbkk
.kbk....kblbbBbblBk
kbk.....klbBkkBblBk
kk......klbBkkBblBk
........kblbbBbbBBk
.........kkbBBBkk
...........kkkk
"""

CITY = [
    ('prop_insula', insula, 'apartment block (insula): shops at street level, a timber balcony and three floors of small windows'),
    ('prop_insula_b', insula_b, 'smaller apartment block in bare brick with travertine string courses and an arched shop'),
    ('prop_domus', domus, 'town house (domus): blind street wall, tall doorway, the atrium roof with its open compluvium behind'),
    ('prop_thermae', thermae, 'public baths (thermae): vaulted hall with a lunette window, a domed hot room and a smoking furnace flue'),
    ('prop_basilica', basilica, 'basilica: two storeys of marble arcades under a long tiled roof'),
    ('prop_pistrinum', pistrinum, 'bakery (pistrinum): brick oven with a fire, loaves on shelves, two lava millstones and a grain sack'),
    ('prop_tholos', tholos, 'round temple (tholos, like the Temple of Vesta) with a conical roof'),
    ('prop_portico', portico, 'a stretch of colonnade (porticus) under a tiled roof'),
    ('prop_aqueduct', aqueduct, 'three arches of an aqueduct carrying its water channel; the arches are transparent'),
    ('prop_theatre', theatre, 'theatre: the curved outer wall of the seating, two tiers of arcades below an attic'),
    ('prop_obelisk', obelisk, 'red granite obelisk with a gilded tip, as on the spina of the Circus'),
    ('prop_columna', columna, 'honorary column with a spiral of reliefs and a gilded statue on top'),
    ('prop_rostra', rostra, "the Rostra: speakers' platform hung with the bronze rams of captured ships"),
    ('prop_altar', ALTAR, 'marble altar with a garland and a burning offering'),
    ('prop_civis', CIVIS, 'citizen in a toga, standing (static, facing the viewer)'),
    ('prop_matrona', MATRONA, 'woman in a stola with her palla drawn over her head (static)'),
    ('prop_mercator', MERCATOR, 'street seller in a tunic carrying a tray of loaves on his head (static)'),
    ('prop_plaustrum', PLAUSTRUM, 'two-wheeled cart (plaustrum) loaded with amphorae'),
]
def build_city():
    for aid, src, desc in CITY:
        im = src() if callable(src) else GP(src, aid)
        asset(aid, im, file=f'props/{aid}.png', w=im.size[0], h=im.size[1], frames=1, desc=desc + '. Anchor at bottom centre.')
BUILDERS.append(build_city)

# ================================================================== LANDMARKS
# The milestone's inscription field (`face` in assets.json: 17 columns by 17 rows) is flat
# marble. The app carves the week numeral into it with font_roman, on two lines when it is long.
MILESTONE = """
.......kkkkkkk.......
.....kkwmmmmmMkk.....
...kkwmmmmmmmmmMkk...
..kwmmmmmmmmmmmmmMk..
.kwmmmmmmmmmmmmmmmMk.
kwmmmmmmmmmmmmmmmmmMk
kwmmmmmmmmmmmmmmmmmMk
kwmmmmmmmmmmmmmmmmmMk
kwmmmmmmmmmmmmmmmmmMk
kwmmmmmmmmmmmmmmmmmMk
kwmmmmmmmmmmmmmmmmmMk
kwmmmmmmmmmmmmmmmmmMk
kwmmmmmmmmmmmmmmmmmMk
kwmmmmmmmmmmmmmmmmmMk
kwmmmmmmmmmmmmmmmmmMk
kwmmmmmmmmmmmmmmmmmMk
kwmmmmmmmmmmmmmmmmmMk
kwmmmmmmmmmmmmmmmmmMk
kwmmmmmmmmmmmmmmmmmMk
kwmmmmmmmmmmmmmmmmmMk
kwmmmmmmmmmmmmmmmmmMk
kwmmmmmmmmmmmmmmmmmMk
kwmmmmmmmmmmmmmmmmmMk
kSSSSSSSSSSSSSSSSSSSk
kkkkkkkkkkkkkkkkkkkkk
kwmmmmmmmmmmmmmMMMSSk
kSSSSSSSSSSSSSSSSSssk
kkkkkkkkkkkkkkkkkkkkk
"""
FOUNTAIN = """
..........kkkkkkkkkk
.........kwmmmmmmMMSk
..........kkkkkkkkkk
..........kwmmmmMMSk
..........kwmggggMSk
..........kwmgzzgMSk
..........kwmgkkgMSk
..........kwmmAFMMSk
..........kwmmAFMMSk
..........kwmmAFMMSk
.kkkkkkkkkkkkkAFkkkkkkkkkkkkk
kwmmmmmmmmmmmmAFmmmmmmmmmmmMSk
kmkkkkkkkkkkkkFFkkkkkkkkkkkkSk
kmkAAAAAAAAAAFFFFAAAAAAAAAAkSk
kmkAYAAAAYAAFAAAAFAAYAAAAYAkSk
kmkAAAAYAAAAAAAAAAAAAAYAAAAkSk
kmkkkkkkkkkkkkkkkkkkkkkkkkkkSk
kwmmmmmmmmmmmmmmmmmmmmmmmmMMSk
kkkkkkkkkkkkkkkkkkkkkkkkkkkkkk
kwmmmmMmmmmmmMmmmmmmMmmmmMMSSk
kwmmmmMmmmmmmMmmmmmmMmmmmMMSSk
kwmmmmMmmmmmmMmmmmmmMmmmmMMSSk
kwmmmmMmmmmmmMmmmmmmMmmmmMMSSk
kMMMMMMMMMMMMMMMMMMMMMMMMMSSSk
kkkkkkkkkkkkkkkkkkkkkkkkkkkkkk
"""
SHRINE = """
..........kk
.........kggk
.......kkoorRkk
.....kkooorrrRRkk
...kkoooorgrrrrRRkk
.kkooooorrgrrrrrRRRkk
kkkkkkkkkkkkkkkkkkkkkk
kwmmmmmmmmmmmmmmmmmMSk
.kkkkkkkkkkkkkkkkkkkk
.kwmkBBBBBBBBBBBBkmSk
.kwmkBBBBkkkkBBBBkmSk
.kwmkBBBkgEEgkBBBkmSk
.kwmkBBBkgEggkBBBkmSk
.kwmkBBBBkggkBBBBkmSk
.kwmkBBBkgEEgykBBkmSk
.kwmkBBkgEgggyykBkmSk
.kwmkBBkgEgggyykBkmSk
.kwmkBBBkgEggykBBkmSk
.kwmkBBBkgEggykBBkmSk
.kwmkBBBkgggyykBBkmSk
.kwmkBBkkkkkkkkkBkmSk
.kwmkBBkSmmmmMSkBkmSk
kkkkkkkkkkkkkkkkkkkkkk
kwmmmmmmmmmmmmmmmmmMSk
.kkkkkkkkkkkkkkkkkkkk
..kwmmmmmmmmmmmmMMSk
..kwmmvevxevevmmMMSk
..kwmmmmmmmmmmmmMMSk
..kwmmmmmmmmmmmmMMSk
.kwmmmmmmmmmmmmmmMMSk
.kkkkkkkkkkkkkkkkkkkk.
"""

def arch():
    W, H = 56, 44
    cv = Cv(W, H)
    cx, cy = 27.5, 31.0
    for y in range(18, H):                                   # piers, spandrels and the arched opening
        for x in range(1, 55):
            d = math.hypot(x - cx, y - cy)
            if (y >= cy and 15 <= x <= 40) or (y < cy and d <= 12.7): continue
            if y >= cy and x in (14, 41): c = 'k'
            elif y < cy and d <= 13.7: c = 'k'
            elif y < cy and d <= 15.7: c = 'c' if x < 30 else 'p'
            elif y < cy and d <= 16.6: c = 'n'
            else:
                c = 'p'
                if (x < 14 or x > 41) and y % 5 == 3: c = 'n'
                if x == 1 or x == 42: c = 'c'
                if x == 13 or x == 54: c = 'n'
            cv.set(x, y, c)
    for x in (5, 46):                                        # engaged columns
        for y in range(20, 38): cv.grid(x, y, "ccpnt")
        cv.hline(x - 1, x + 5, 18, 'c'); cv.hline(x - 1, x + 5, 19, 'n'); cv.hline(x - 1, x + 5, 38, 'c'); cv.hline(x - 1, x + 5, 39, 'n')
    for a, b in ((1, 13), (42, 54)):                         # plinths
        cv.rect(a, 40, b, 42, 't'); cv.hline(a, b, 40, 'n'); cv.hline(a, b, 43, 'k')
    cv.hline(0, 14, 43, 'k'); cv.hline(41, 55, 43, 'k')
    cv.vline(0, 14, 43, 'k'); cv.vline(55, 14, 43, 'k')
    cv.grid(16, 20, "gg\ngy"); cv.grid(38, 20, "gg\ngy")     # gilt roundels in the spandrels
    cv.rect(0, 14, 55, 17, 'k'); cv.hline(1, 54, 15, 'c'); cv.hline(1, 54, 16, 'p')        # entablature
    cv.rect(0, 0, 55, 13, 'k'); cv.hline(1, 54, 1, 'c')                                    # attic
    cv.rect(1, 2, 54, 12, 'p'); cv.vline(1, 2, 12, 'c'); cv.vline(54, 2, 12, 'n'); cv.hline(1, 54, 13, 'n')
    cv.rect(9, 2, 46, 12, 'g'); cv.hline(9, 46, 12, 'y'); cv.vline(46, 2, 12, 'y')         # gold frame
    cv.rect(10, 3, 45, 11, 'm'); cv.hline(10, 45, 11, 'S')                                                            # inscription panel (numerals go here)
    cv.grid(26, 16, "kcck\nkcpk\nkcpk\n.kk.")                                              # keystone
    return cv.img('arch')

def capitolium():
    W, H = 96, 72
    cv = Cv(W, H)
    cv.rect(11, 29, 84, 57, 'k'); cv.rect(12, 30, 83, 57, 'S'); cv.rect(12, 30, 83, 32, 's')      # cella, in the shade of the porch
    cv.rect(41, 36, 54, 57, 'k'); cv.rect(42, 37, 53, 57, 'm'); cv.rect(43, 38, 52, 57, 'k')      # door frame
    cv.rect(44, 39, 51, 57, 'z'); cv.vline(47, 39, 57, 'B'); cv.vline(48, 39, 57, 'y')            # bronze doors
    for y in (42, 47, 52):
        for x in (45, 50): cv.set(x, y, 'g'); cv.set(x, y + 1, 'y')
    for x in (12, 25, 38, 52, 65, 78): temple_column(cv, x, 30, 57)
    cv.rect(8, 23, 87, 29, 'k'); cv.hline(9, 86, 24, 'w'); cv.hline(9, 86, 25, 'm')               # entablature
    cv.rect(9, 26, 86, 27, 'M'); cv.hline(9, 86, 28, 'S')
    for x in range(15, 82, 3): cv.set(x, 26, 'g'); cv.set(x, 27, 'y')                             # gilded inscription
    pediment(cv, 95, 3, 23, 3, 46, 'y')
    cv.grid(45, 12, "..gg..\n.gEEg.\n..gg..\n.gEEg.\ngEEEEg\ngEggEg\n.gEEg.\n.gEEg.\ngg..gg")     # Jupiter and attendants
    for x in (36, 56): cv.grid(x, 15, ".gg.\n.gg.\ngEEg\ngEEg\n.gg.\ng..g")
    for x in (28, 64): cv.grid(x, 18, ".gg.\ngEEg\ngEEg")
    cv.grid(21, 20, "gEgg"); cv.grid(71, 20, "ggEg")
    cv.grid(44, 0, "..gEEg..\n.gEgEEg.\ngEEggEEy\n.gyggyy.")                                      # quadriga on the apex
    cv.grid(2, 20, "gEg\n.g."); cv.grid(91, 20, "gEy\n.y.")
    steps(cv, 12, 83, 58, 7)
    return cv.img('capitolium')

def build_landmarks():
    for aid, text in [('landmark_milestone', MILESTONE), ('landmark_fountain', FOUNTAIN), ('landmark_shrine', SHRINE)]:
        im = GP(text, aid); asset(aid, im, w=im.size[0], h=im.size[1], frames=1)
    for aid, fn in [('landmark_arch', arch), ('landmark_capitolium', capitolium)]:
        im = fn(); asset(aid, im, w=im.size[0], h=im.size[1], frames=1)
    # where the app carves the numeral: [x, y, w, h] inside the sprite
    META['landmark_milestone'].update(face=[2, 6, 17, 17], desc='Roman milestone (miliarium). `face` is its flat marble inscription field; the week number is carved there with font_roman, on two lines (tens above units) when it is too long for one. Anchor at bottom centre.')
    META['landmark_arch'].update(face=[10, 4, 36, 7], desc='triumphal arch spanning the road where the chapter changes; `face` is the marble panel in the gold frame on the attic, which takes the chapter numeral. Anchor at bottom centre.')
BUILDERS.append(build_landmarks)

# ================================================================== UI
DISC = """
....kkkk....
..kk1112kk..
.k11122223k.
.k11222223k.
k1122222233k
k1222222233k
k1222222333k
k2222223333k
.k22223333k.
.k22333333k.
..kk3333kk..
....kkkk....
"""
def waypoint(tones, emblem=None, at=(4, 4)):
    im = G(DISC, 'disc', remap=dict(zip('123', tones)))
    if emblem: put(im, G(emblem, 'wp'), *at)
    return im

# Roman numerals: ink strokes 7 high on a transparent ground, carved by the app into the
# marble of milestones and arches. `widths` in assets.json lets glyphs differ in width;
# at present all seven are three wide.
GLYPHS = {
    'I': "###\n.#.\n.#.\n.#.\n.#.\n.#.\n###", 'V': "#.#\n#.#\n#.#\n#.#\n#.#\n#.#\n.#.",
    'X': "#.#\n#.#\n#.#\n.#.\n#.#\n#.#\n#.#", 'L': "#..\n#..\n#..\n#..\n#..\n#..\n###",
    'C': ".##\n#..\n#..\n#..\n#..\n#..\n.##", 'D': "##.\n#.#\n#.#\n#.#\n#.#\n#.#\n##.",
    'M': "#.#\n###\n###\n#.#\n#.#\n#.#\n#.#",
}
FONT_ORDER = 'IVXLCDM'
FONT_CELL = 4                                              # glyphs sit left-aligned in cells this far apart
def font_roman():
    im = new(FONT_CELL * len(FONT_ORDER), 7); px = im.load()
    for i, ch in enumerate(FONT_ORDER):
        for y, row in enumerate(GLYPHS[ch].split('\n')):
            for x, c in enumerate(row):
                if c == '#': px[i * FONT_CELL + x, y] = rgb('ink')
    return im

def ui_frame():
    """24x24 nine-slice: every edge strip is constant along its length, so it stretches cleanly"""
    cv = Cv(24, 24)
    for y in range(24):
        for x in range(24):
            d = min(x, y, 23 - x, 23 - y)
            lit = min(x, y) <= min(23 - x, 23 - y)
            cv.set(x, y, {0: 'k', 1: 'o' if lit else 'R', 2: 'r', 3: 'r', 4: 'p', 5: 'R'}.get(d, 'p'))
    stud = ".kkk.\nkgEgk\nkEgyk\nkgyyk\n.kkk."
    for x, y in ((1, 1), (18, 1), (1, 18), (18, 18)): cv.grid(x, y, stud)
    return cv.img('ui_frame')

def ui_tablet():
    cv = Cv(48, 24)
    for i in range(5):                                       # dovetail handles (ansae)
        half = 2 + i
        for y in range(12 - half, 12 + half):
            cv.set(5 - i, y, 'm'); cv.set(42 + i, y, 'M')
    cv.outline()
    cv.rect(6, 1, 41, 22, 'k'); cv.rect(7, 2, 40, 21, 'm')
    cv.hline(7, 40, 2, 'w'); cv.vline(7, 2, 21, 'w'); cv.hline(7, 40, 21, 'S'); cv.vline(40, 2, 21, 'S')
    cv.vline(6, 10, 13, 'm'); cv.vline(41, 10, 13, 'M')
    for a, c in ((0, 'M'), (1, 'w')):                         # carved inner border: a dark line with a lit lip
        x0, y0, x1, y1 = 10 + a, 5 + a, 37 + a, 18 + a
        if a: cv.hline(x0, x1 - 1, y1, c); cv.vline(x1, y0, y1, c)
        else:
            cv.hline(x0, x1, y0, c); cv.hline(x0, x1, y1, c); cv.vline(x0, y0, y1, c); cv.vline(x1, y0, y1, c)
    return cv.img('ui_tablet')

# ---- coins: a turned disc per metal with an embossed relief. The relief is drawn as a mask
# ('#' raised, 'o' an engraved detail); its upper-left edges catch the light, its lower-right
# edges fall into shadow. Tones: 1 raised, 2 field, 3 shadow, 4 glint.
HEAD = """
....#####
..#########
.###########
.###########
.#######o###
.############
.###########
..#########
..##########
...########
....#####
....#####
...#######
.###########
#############
"""
PROW = """
.........#
........##
##......###
###...######
#############
.############
..##########
...########
"""
WREATH_MARKS = """
....o.o.o
..o.o
.o.o
.o
"""
RAYS = """
..#..#..#.#
..#..#..#.#
..#..#.#..#
"""
HELMET = """
..###.
.##########
.ooooooooooo#
"""
VICTORY = """
....##
...####
....##...#
...####.###
..######.###
.#.####.####
...####..##
...####
..######
..######
.########
"""
METALS = {
    'bronze':  dict(zip('1234', 'lbBt')),
    'brass':   dict(zip('1234', 'yzBg')),
    'orich':   dict(zip('1234', 'gyzE')),
    'silver':  dict(zip('1234', 'mSsw')),
    'silver2': dict(zip('1234', 'mSDw')),
    'gold':    dict(zip('1234', 'Egyw')),
}
def coin(metal, r, parts):
    cv = Cv(24, 24); c = 11.5
    for y in range(24):
        for x in range(24):
            d = math.hypot(x - c, y - c)
            if d > r: continue
            lit = (x - c) + (y - c) < 0
            if d > r - 1: ch = 'k'
            elif d > r - 2.5: ch = '1' if lit else '3'          # raised rim
            elif d > r - 3.4: ch = '3' if lit else '1'          # the rim's inner edge
            else: ch = '2'
            cv.set(x, y, ch)
    raised, cut = set(), set()
    for text, ox, oy, mirror in parts:
        for j, row in enumerate(rows_of(text)):
            for i, chr_ in enumerate(row):
                if chr_ == '.': continue
                xs = [ox + i] + ([23 - (ox + i)] if mirror else [])
                for x in xs:
                    if math.hypot(x - c, oy + j - c) > r - 3.4: continue
                    raised.add((x, oy + j))
                    (cut.add if chr_ == 'o' else cut.discard)((x, oy + j))
    for x, y in raised:
        ch = '1'
        if (x - 1, y) not in raised or (x, y - 1) not in raised: ch = '4'
        elif (x + 1, y) not in raised or (x, y + 1) not in raised: ch = '3'
        if (x, y) in cut: ch = '3'
        cv.set(x, y, ch)
        for dx, dy in ((1, 0), (0, 1)):                         # cast shadow on the field
            if (x + dx, y + dy) not in raised and cv.get(x + dx, y + dy) == '2': cv.set(x + dx, y + dy, '3')
    return G('\n'.join(''.join(row) for row in cv.g), 'coin', remap=METALS[metal])

# ---- 20x20 icons
ICON_TUNIC = """
....................
.....kkkkkkkkkk.....
...kkccckkkkcccpkk..
.kkcccccppppccccpnkk
kccccccccccccccccpnk
kcccckccccccccpkcpnk
kcckkkccccccccpkkknk
.kk..kccccccccpk.kk.
.....kccccccccpk....
.....kbbbbbbbbBk....
.....kccccccccpk....
.....kcccpccccpk....
....kccccpcccccpk...
....kccccpccpccpk...
....kcccpccccpcpnk..
...kccccpccccpccpnk.
...kccccpccccpccpnk.
...kkkkkkkkkkkkkkkk.
....................
....................
"""
ICON_TOGA = """
....................
....................
....kkkkkkkkkkkkk...
...kwwwwwwwwwwwwmk..
..kwwwwwwwwwwwwmmSk.
..kPPPPPPPPPPPPPWSk.
..kwwwwwwwwwwwwmmSk.
.kkkkkkkkkkkkkkkkSk.
.kwwwwwwwwwwwwwmkSk.
.kwwwwmwwwwwwwmmkkk.
.kPPPPPPPPPPPPPWk...
.kwwwwwwwwwwwwmmk...
.kwwmwwwwwwmwwmSk...
.kmmmmmmmmmmmmSSk...
..kkkkkkkkkkkkkk....
....................
....................
....................
....................
....................
"""
ICON_CLOAK = """
.......kkkkkk.......
......kooorrRk......
.....koorkkrrRk.....
.....korkKKkrRk.....
.....korkKKkrRk.....
....kkoorkkrrRkk....
...koooorggrrrrRk...
..koooorrggrrrrrRk..
..kooorrrrrrRrrrRk..
.kooorrrrrrrRrrrRRk.
.koorrrrrrrrRrrrRRk.
.koorrrRrrrrRrrrRRk.
kooorrrRrrrrrRrrrRRk
koorrrrRrrrrrRrrrRRk
koorrrrRrrrrrRrrRRRk
.korrrrRrrrrRrrRRRk.
.kkrrrRrrrrrRrRRRkk.
...kkkkrrrRRkkkkk...
.......kkkkkk.......
....................
"""
ICON_LAUREL = """
....................
.....kk......kk.....
....kfek....kefk....
...kfevk....kvefk...
..kkevk......kvekk..
.kfekk........kkefk.
.kevk..........kvek.
kfevk..........kvefk
kevk............kvek
kkfek..........kefkk
kfevk..........kvefk
.kevk..........kvek.
.kkfek........kefkk.
..kevfk......kfvek..
..kkevek....kevekk..
...kkevfkkkkfvekk...
.....kkevxxvekk.....
.......kxxxxk.......
......kxk..kxk......
......kk....kk......
"""
ICON_SATCHEL = """
....................
......kkkkkkkk......
.....kBkkkkkkBk.....
....kBk......kBk....
....kBk......kBk....
..kkkBkkkkkkkkBkkk..
.klltllllllllllllBk.
.kltllllllllllllbBk.
.kllllllllllllllbBk.
.kbbbbbbkggkbbbbbBk.
.kllllllkgEkllllbBk.
.klllllllkklllllbBk.
.kltllllllllllllbBk.
.klllllllllllllbbBk.
.klllllllllllllbbBk.
.kbbbbbbbbbbbbbbBBk.
..kkkkkkkkkkkkkkkk..
....................
....................
....................
"""
ICON_STREAK = """
....................
.........kk.........
........kok.........
........koRk........
.......koorRk.......
......kooyrRk.......
......koygorRk.k....
.....kooyggorRkok...
....kooygEgyorkoRk..
....koygEEggyoorRk..
...kooygEEEggyorRk..
...koyggEwEEgyorRk..
...koygEEwwEgyorRk..
...korygEwwEgyrRRk..
....korygEEgyrRRk...
....kkorryyyrRRkk...
......kkRRRRRkk.....
........kkkkk.......
....................
....................
"""
ICON_SCROLL = """
....................
....................
.kkk............kkk.
klBBk..........klBBk
kkkkkkkkkkkkkkkkkkkk
kpnkccccccccccccknpk
kpnkclllclllllccknpk
kpnkccccccccccccknpk
kpnkcllllllclllcknpk
kpnkccccccccccccknpk
kpnkcllclllllcccknpk
kpnkccccccccccccknpk
kpnkclllllcllllcknpk
kpnkccccccccccccknpk
kkkkkkkkkkkkkkkkkkkk
klBBk..........klBBk
.kkk............kkk.
....................
....................
....................
"""
LETTER_L = """
ccc...
.cc...
.cc...
.cc...
.cc...
.cc..c
.ccccc
cccccc
"""

def app_icon_art(size):
    """a laurel wreath around a cream L on terracotta. On the 32px grid the wreath stays inside
    the middle 65% (safe under any maskable crop); the 24px grid fills an ordinary icon better."""
    o = (size - 20) // 2
    im = new(size, size, rgb('terra'))
    put(im, G(ICON_LAUREL, 'wreath'), o, o)
    put(im, G(LETTER_L, 'L', remap={'c': 'R'}), o + 8, o + 5)
    put(im, G(LETTER_L, 'L'), o + 7, o + 4)
    return im

def build_ui():
    asset('wp_locked', waypoint('SsD'), w=12, h=12, frames=1)
    asset('wp_done', waypoint('orR', ".gg.\ngEgy\ngggy\n.yy."), w=12, h=12, frames=1)
    asset('wp_current', waypoint('Egy', ".ww.\nwwwE\nwwEE\n.EE."), w=12, h=12, frames=1)
    asset('wp_rest', waypoint('YAa', ".ww.\nwFFA\nwFAA\n.AA."), w=12, h=12, frames=1)
    for cid, metal, r, parts in [
            ('as', 'bronze', 10.5, [(PROW, 5, 8, False)]),
            ('dupondius', 'brass', 11.0, [(HEAD, 5, 6, False), (RAYS, 5, 3, False)]),
            ('sestertius', 'orich', 11.9, [(HEAD, 5, 5, False), (WREATH_MARKS, 5, 5, False)]),
            ('quinarius', 'silver', 9.5, [(VICTORY, 6, 6, False)]),
            ('denarius', 'silver2', 10.5, [(HEAD, 5, 5, False), (HELMET, 5, 4, False)]),
            ('aureus', 'gold', 11.0, [(HEAD, 5, 5, False), (WREATH_MARKS, 5, 5, False)])]:
        asset('coin_' + cid, coin(metal, r, parts), w=24, h=24, frames=1)
    for iid, text in [('tunic', ICON_TUNIC), ('toga', ICON_TOGA), ('cloak', ICON_CLOAK), ('laurel', ICON_LAUREL),
                      ('satchel', ICON_SATCHEL), ('streak', ICON_STREAK), ('scroll', ICON_SCROLL)]:
        asset('icon_' + iid, G(text, 'icon_' + iid), w=20, h=20, frames=1)
    asset('ui_frame', ui_frame(), w=24, h=24, frames=1, slice=8)
    asset('ui_tablet', ui_tablet(), w=48, h=24, frames=1)
    asset('font_roman', font_roman(), w=3, h=7, frames=7, glyphs=FONT_ORDER, advance=FONT_CELL,
          widths=[len(GLYPHS[c].split('\n')[0]) for c in FONT_ORDER], gap=1,
          desc='Bitmap font sheet: glyphs I V X L C D M in that order, ink on transparent, 7 high. Each glyph sits left-aligned in a cell; cells are `advance` (4) apart, so the sheet is 28x7. `widths` is each glyph\'s width and `gap` the space the app leaves between glyphs.')
    small, big = app_icon_art(24), app_icon_art(32)
    asset('app_icon_192', small.resize((192, 192), Image.NEAREST), w=192, h=192, frames=1)          # 24px art x8
    asset('app_icon_512', big.resize((512, 512), Image.NEAREST), w=512, h=512, frames=1)            # 32px art x16 (maskable)
    i180 = new(180, 180, rgb('terra')); i180.paste(small.resize((168, 168), Image.NEAREST), (6, 6))  # 24px art x7 + field
    asset('app_icon_180', i180, w=180, h=180, frames=1)
BUILDERS.append(build_ui)

# ==== SECTIONS ====

def build_all():
    for b in BUILDERS: b()

# ================================================================== output
def contact_sheet(scale=4, cols_px=1500):
    """every asset at `scale`x on a neutral ground, with the hero layers stacked"""
    pad = 6
    items = []
    for aid, im in OUT.items():
        if aid.startswith('app_icon') and im.size[0] > 192: continue
        s = 1 if aid.startswith('app_icon') else scale
        items.append((aid, im.resize((im.size[0] * s, im.size[1] * s), Image.NEAREST)))
    if 'hero_base' in OUT:
        stack = OUT['hero_base'].copy()
        for l in ('cloak', 'toga', 'satchel', 'laurel'):
            if 'hero_' + l in OUT: stack.alpha_composite(OUT['hero_' + l])
        items.insert(1, ('hero (all layers)', stack.resize((stack.size[0] * scale, stack.size[1] * scale), Image.NEAREST)))
    x = y = pad; rowh = 0; pos = []
    for aid, im in items:
        if x + im.size[0] + pad > cols_px and x > pad:
            x = pad; y += rowh + pad; rowh = 0
        pos.append((aid, im, x, y)); x += im.size[0] + pad; rowh = max(rowh, im.size[1])
    sheet = Image.new('RGBA', (cols_px, y + rowh + pad), rgb('sage'))
    for aid, im, x, y in pos:
        sheet.alpha_composite(im, (x, y))
    return sheet

def write_all():
    mpath = os.path.join(ASSETS, 'assets.json')
    M = json.load(open(mpath, encoding='utf-8'))
    for aid, im in OUT.items():
        a = M['assets'].get(aid)
        if a is None:
            if 'file' not in META[aid]: raise SystemExit(f'{aid} is not in assets.json')
            a = M['assets'][aid] = {'id': aid}
        a.update(META[aid])
        if aid.startswith('prop_'):                         # say where the map uses it
            row = [k for k, d in M['districts'].items() if aid in d.get('buildings', [])]
            loose = [k for k, d in M['districts'].items() if aid in d['props']]
            a['use'] = '; '.join(t for t in (
                'Map: built in rows in the city districts: ' + ', '.join(row) if row else '',
                'Map decoration scattered beside the road in districts: ' + ', '.join(loose) if loose else '') if t) or 'Map decoration (not placed in any district yet)'
            a['desc'] = a.pop('desc')                       # keep desc last
        path = os.path.normpath(os.path.join(ASSETS, a['file']))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        im.save(path, optimize=True)
    for name in EXTRA: M['palette'][name] = PAL[name]
    missing = [k for k in M['assets'] if k not in OUT]
    if missing: raise SystemExit('assets.json entries with no final art: ' + ', '.join(missing))
    with open(mpath, 'w', encoding='utf-8') as f:
        json.dump(M, f, indent=1, ensure_ascii=False)
    print(f'wrote {len(OUT)} assets')

def check_pixels():
    """hard edges only: every pixel is fully opaque or fully transparent"""
    for aid, im in OUT.items():
        for a in set(im.getchannel('A').getdata()):
            if a not in (0, 255): raise SystemExit(f'{aid}: semi-transparent pixel (alpha {a})')

if __name__ == '__main__':
    build_all()
    check_pixels()
    if '--sheet' in sys.argv:
        p = sys.argv[sys.argv.index('--sheet') + 1]
        contact_sheet().save(p); print('contact sheet ->', p)
    if '--check' not in sys.argv:
        write_all()
