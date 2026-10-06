"""Straßenansicht: Wer auf die Stadt klickt, steht plötzlich mitten in der Straße.

Einpunkt-Perspektive, links und rechts Hochhäuser, deren Höhe und beleuchtete Fenster aus den
Wochen der letzten Monate kommen (nächste Wand = jüngste Woche). Die vier Zahlen hängen als
Leuchtreklamen an den Hauswänden.
"""
import math
import random

from common import fmt_int, tr
import render as R
from render import mix, path, rect_d, rects, svg_doc

SW, SH = 830, 460
CX, HY, F = 415, 250, 300          # Bildmitte, Horizont, Brennweite in px
CAM = 1.6                          # Augenhöhe in m
HALF = 9.0                         # Straßenhälfte bis zur Hauswand
ROAD = 4.6                         # Fahrbahnhälfte (außen Gehweg)
ZMIN, ZMAX = 2.0, 78.0

FOG = "#131d44"


def P(x, y, z):
    return CX + F * x / z, HY - F * (y - CAM) / z


def fog(color, z):
    return mix(color, FOG, min(0.75, z / ZMAX * 0.8))


def poly(pts):
    return "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + "Z"


def quad_wall(side, z0, z1, y0, y1):
    x = side * HALF
    return [P(x, y0, z0), P(x, y0, z1), P(x, y1, z1), P(x, y1, z0)]


def sprite(rows, colors, x, y, px):
    out = {}
    for r, line in enumerate(rows):
        for c, ch in enumerate(line):
            if ch in colors:
                out.setdefault(colors[ch], []).append(rect_d(x + c * px, y + r * px, px, px))
    return "".join(path("".join(d), col) for col, d in out.items())


PERSON = [
    "..hhhh..",
    ".hhhhhh.",
    ".hhhhhh.",
    "..hhhh..",
    ".bbbbbb.",
    "abbbbbba",
    "abbbbbba",
    "abbbbbba",
    "abbbbbba",
    ".bbbbbb.",
    ".ll..ll.",
    ".ll..ll.",
    ".ll..ll.",
    ".ss..ss.",
    ".ss..ss.",
]


def street(cfg, model, accent):
    rng = random.Random(11)
    bright = mix(accent, "#ffffff", 0.6)
    body = []

    # Himmel
    for i, color in enumerate(R.SKY):
        y0 = [0, 70, 130, 190, 240][i]
        y1 = [70, 130, 190, 240, HY + 6][i]
        body.append(rects(0, y0, SW, y1 - y0, color))
    stars, big = [], []
    for _ in range(70):
        x, y = rng.randrange(330, 500) // 2 * 2, rng.randrange(2, 210) // 2 * 2
        (big if rng.random() < 0.15 else stars).append(rect_d(x, y, 2, 2))
    body.append(path("".join(stars), "#aab6ee") + path("".join(big), "#ffffff"))
    body.append(R.moon(CX + 2, 60, 16))

    # ferne Silhouette am Ende der Straße
    far = []
    x = CX - 40
    while x < CX + 40:
        w = rng.randrange(6, 14) // 2 * 2
        h = rng.randrange(14, 42) // 2 * 2
        far.append(rect_d(x, HY - h, w, h + 8))
        x += w
    body.append(path("".join(far), "#0b1230"))

    # Boden: Fahrbahn und Gehwege
    gz = (ZMIN, ZMAX)
    road = [P(-ROAD, 0, gz[0]), P(-ROAD, 0, gz[1]), P(ROAD, 0, gz[1]), P(ROAD, 0, gz[0])]
    body.append(rects(0, HY, SW, SH - HY, R.GROUND))
    body.append(path(poly(road), R.PAVE))
    for side in (-1, 1):
        walk = [P(side * ROAD, 0, gz[0]), P(side * ROAD, 0, gz[1]), P(side * HALF, 0, gz[1]), P(side * HALF, 0, gz[0])]
        body.append(path(poly(walk), "#18204a"))
        curb = [P(side * ROAD, 0, gz[0]), P(side * ROAD, 0, gz[1]), P(side * (ROAD + 0.25), 0, gz[1]), P(side * (ROAD + 0.25), 0, gz[0])]
        body.append(path(poly(curb), "#2a3668"))
    dashes = []
    z = 7.0
    while z < ZMAX - 4:
        dashes.append(poly([P(-0.12, 0, z), P(-0.12, 0, z + 1.6), P(0.12, 0, z + 1.6), P(0.12, 0, z)]))
        z += 4.5
    body.append(path("".join(dashes), "#2e3a6e"))

    # Häuserwände
    weekly = model["weekly"][-26:][::-1]           # jüngste Woche zuerst
    counts = model["weeks"][-26:][::-1]
    maxw = max(weekly + [1])
    walls, offs, ons, hots, roofs = [], {}, [], [], []
    for side in (-1, 1):
        z = ZMIN
        k = 0 if side < 0 else 1
        i = 0
        while z < ZMAX:
            depth = rng.choice((6, 7, 8, 9, 10))
            z1 = min(z + depth, ZMAX)
            idx = (i * 2 + (0 if side < 0 else 1)) % len(weekly)
            act = math.sqrt(weekly[idx] / maxw) if maxw else 0
            h = 15 + 22 * act + rng.randrange(0, 4)
            base = R.WALL_A if (i + k) % 2 == 0 else R.WALL_B
            zc = (z + z1) / 2
            walls.append((fog(base, zc), quad_wall(side, z, z1 - 0.15, 0, h)))
            # Dach-Kante und Gesims
            roofs.append((fog("#2a3668", zc), quad_wall(side, z, z1 - 0.15, h - 0.5, h)))
            # Fenster
            days = [v for _, v in counts[idx]]
            lit_p = 0.10 + 0.55 * (sum(1 for v in days if v) / 7)
            cols = max(2, int((z1 - z - 0.6) // 1.9))
            rows = int((h - 3.5) // 3.0)
            for ci in range(cols):
                za = z + 0.6 + ci * ((z1 - z - 0.6) / cols)
                zb = za + ((z1 - z - 0.6) / cols) * 0.55
                for ri in range(rows):
                    ya = 3.2 + ri * 3.0
                    yb = ya + 1.5
                    pts = quad_wall(side, za, zb, ya, yb)
                    xs = [p[0] for p in pts]
                    if max(xs) - min(xs) < 1.2:
                        continue
                    r = rng.random()
                    if r < lit_p:
                        (hots if r < lit_p * 0.25 else ons).append(poly(pts))
                    else:
                        offs.setdefault(fog(R.WINDOW_OFF, zc), []).append(poly(pts))
            # Erdgeschoss-Laden: dunkle Eingänge
            door = quad_wall(side, z + 1.0, z + 2.8, 0, 2.6)
            walls.append((fog("#0a0f22", zc), door))
            z = z1
            i += 1
    for color, pts in sorted(walls, key=lambda t: 0):
        body.append(path(poly(pts), color))
    body.append("".join(path(poly(p), c) for c, p in roofs))
    for color, polys in offs.items():
        body.append(path("".join(polys), color))
    body.append(path("".join(ons), accent) + path("".join(hots), bright))

    # Straßenlaternen mit Lichtpfützen
    lamp = []
    for side, z in ((-1, 7), (1, 11), (-1, 16), (1, 24), (-1, 34), (1, 48)):
        x = side * (ROAD + 0.9)
        bx, by = P(x, 0, z)
        tx, ty = P(x, 5.4, z)
        wpx = max(2, int(F * 0.18 / z) // 2 * 2)
        lamp.append(rects(int(bx) - wpx // 2, int(ty), wpx, int(by - ty), "#2a3668"))
        hx, hy = P(x - side * 0.9, 5.5, z)
        lamp.append(rects(int(min(hx, tx)), int(ty) - wpx, int(abs(hx - tx)) + wpx, wpx, "#2a3668"))
        hr = max(3, int(F * 0.45 / z))
        lamp.append(f'<path d="{rect_d(int(hx) - hr, int(hy) - hr // 2, hr * 2, hr)}" fill="{bright}"/>')
        lamp.append(f'<path d="{rect_d(int(hx) - hr * 2, int(hy) - hr, hr * 4, hr * 2)}" fill="{accent}" fill-opacity=".10"/>')
        pool = poly([P(x - 2.4, 0, z - 1.4), P(x + 2.4, 0, z - 1.4), P(x + 2.4, 0, z + 1.8), P(x - 2.4, 0, z + 1.8)])
        lamp.append(f'<path d="{pool}" fill="{accent}" fill-opacity=".07"/>')
    body.append("".join(lamp))

    # Leuchtreklamen an den Wänden
    signs = [
        (fmt_int(cfg, model["year_total"]), tr(cfg, "sign_year")),
        (fmt_int(cfg, model["active_days"]), tr(cfg, "sign_days")),
        (fmt_int(cfg, model["longest"]), tr(cfg, "sign_streak")),
        (fmt_int(cfg, model["total"]), tr(cfg, "sign_total")),
    ]
    sw_, sh_ = 152, 64
    spots = [(-1, 9.5), (1, 14.0), (-1, 21.0), (1, 25.0)]
    placed = []
    for k, ((num, label), (side, z)) in enumerate(zip(signs, spots)):
        wm = 3.4                                    # Breite in m
        scale = (F * wm / z) / sw_
        x_in = side * (HALF - wm) if side > 0 else -HALF
        sx, sy = P(x_in, 8.2, z)
        # Arm zur Wand
        ax = P(side * HALF, 7.0, z)[0]
        arm = rects(int(min(ax, sx + sw_ * scale * (0 if side > 0 else 1))), int(sy + sh_ * scale * 0.5),
                    max(2, int(abs(ax - (sx + (0 if side > 0 else sw_ * scale))))), 2, "#2a3668")
        g = (f'<g transform="translate({sx:.1f} {sy:.1f}) scale({scale:.3f})">'
             f'{R.sign_board(0, 0, sw_, sh_, num, label, accent, round(k * 1.7, 1))}</g>')
        placed.append((z, arm + g))
    body.append("".join(g for _, g in sorted(placed, key=lambda t: -t[0])))

    # Spiegelungen der Reklamen auf der nassen Straße
    refl = []
    for k, (side, z) in enumerate(spots):
        x = side * 2.6
        a, b = P(x - 1.2, 0, z), P(x + 1.2, 0, z * 0.6 + 1)
        refl.append(f'<path d="{poly([P(x - 1.1, 0, z), P(x + 1.1, 0, z), P(x + 1.6, 0, z * 0.55), P(x - 1.6, 0, z * 0.55)])}" fill="{accent}" fill-opacity=".06"/>')
    body.append("".join(refl))

    zoom = rects(0, 0, SW, SH, "#060a18") + f'<g class="zoom">{"".join(body)}</g>'

    # Person von hinten, schaut die Straße hinunter
    px = 4
    pw, ph = 8 * px, len(PERSON) * px
    figure = sprite(PERSON, {"h": "#3a4784", "b": "#2a3668", "a": "#222c58", "l": "#161d3e", "s": "#05070f"},
                    CX - pw // 2, SH - ph - 10, px)
    shadow = rects(CX - pw // 2 - 6, SH - 10, pw + 12, 4, "#05070f", 'fill-opacity=".5"')
    rim = rects(CX - pw // 2, SH - ph - 10 + 3 * px, px, px * 2, "#9fb0e8", 'fill-opacity=".5"')

    alt = tr(cfg, "alt_street").format(
        year=fmt_int(cfg, model["year_total"]), days=fmt_int(cfg, model["active_days"]),
        streak=fmt_int(cfg, model["longest"]), total=fmt_int(cfg, model["total"]))
    return svg_doc(SW, SH, alt, zoom + shadow + figure + rim), SH, alt
