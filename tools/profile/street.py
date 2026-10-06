"""Straßen-Klickspiel: Aus der Stadt wird eine begehbare Straße.

GitHub erlaubt in READMEs nur Klicks auf Bilder. Das Spiel besteht deshalb aus Seiten (Markdown) und
Bildern: Jeder Schritt auf der Straße ist ein Bild aus einer anderen Kameraposition, aufgeteilt in
drei anklickbare Streifen (links = linke Tür, Mitte = weitergehen, rechts = rechte Tür). Hinter jeder
Tür liegt ein Raum mit einem Projekt.
"""
import math
import random

from common import fmt_int, tr
import render as R
from render import mix, path, rect_d, rects

SW, SH = 830, 460
CX, HY, F = 415, 250, 300          # Bildmitte, Horizont, Brennweite in px
CAM = 1.6                          # Augenhöhe in m
HALF = 9.0                         # Straßenhälfte bis zur Hauswand
ROAD = 4.6                         # Fahrbahnhälfte (außen Gehweg)
ZMIN = 2.0                         # nächste sichtbare Entfernung
ZW = 140.0                         # Länge der Welt
FAR = 80.0                         # ab hier maximal Nebel
FOG = "#131d44"

STEPS = [0.0, 8.0, 22.0]           # Kamerapositionen entlang der Straße
DOORS = [(-1, 14.0), (1, 14.0), (-1, 28.0), (1, 28.0)]   # (Seite, Welt-z) je Projekt
CUTS = (300, 530)                  # Trennlinien der drei Klickstreifen


def poly(pts):
    return "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + "Z"


class Cam:
    def __init__(self, dz):
        self.dz = dz

    def rel(self, z):
        return z - self.dz

    def P(self, x, y, z):
        r = z - self.dz
        return CX + F * x / r, HY - F * (y - CAM) / r

    def wall(self, side, z0, z1, y0, y1):
        x = side * HALF
        return [self.P(x, y0, z0), self.P(x, y0, z1), self.P(x, y1, z1), self.P(x, y1, z0)]

    def fog(self, color, z):
        return mix(color, FOG, min(0.75, max(0, z - self.dz) / FAR * 0.8))


# ---------------------------------------------------------------- Welt (einmal berechnet)

def build_world(model):
    rng = random.Random(11)
    weekly = model["weekly"][-26:][::-1]
    counts = model["weeks"][-26:][::-1]
    maxw = max(weekly + [1])
    buildings = []
    for side in (-1, 1):
        z, i = 0.0, 0
        while z < ZW:
            depth = rng.choice((6, 7, 8, 9, 10))
            z1 = min(z + depth, ZW)
            idx = (i * 2 + (0 if side < 0 else 1)) % len(weekly)
            act = math.sqrt(weekly[idx] / maxw) if maxw else 0
            h = 15 + 22 * act + rng.randrange(0, 4)
            days = [v for _, v in counts[idx]]
            lit_p = 0.10 + 0.55 * (sum(1 for v in days if v) / 7)
            cols = max(2, int((z1 - z - 0.6) // 1.9))
            rows = int((h - 3.5) // 3.0)
            wins = []
            span = (z1 - z - 0.6) / cols
            for ci in range(cols):
                za = z + 0.6 + ci * span
                for ri in range(rows):
                    r = rng.random()
                    state = 2 if r < lit_p * 0.25 else 1 if r < lit_p else 0
                    wins.append((za, za + span * 0.55, 3.2 + ri * 3.0, 4.7 + ri * 3.0, state))
            buildings.append({"side": side, "z0": z, "z1": z1, "h": h, "alt": (i + (0 if side < 0 else 1)) % 2, "wins": wins})
            z = z1
            i += 1
    return buildings


# ---------------------------------------------------------------- Straßenbild

def sprite(rows, colors, x, y, px):
    out = {}
    for r, line in enumerate(rows):
        for c, ch in enumerate(line):
            if ch in colors:
                out.setdefault(colors[ch], []).append(rect_d(x + c * px, y + r * px, px, px))
    return "".join(path("".join(d), col) for col, d in out.items())


PERSON = [
    "..hhhh..", ".hhhhhh.", ".hhhhhh.", "..hhhh..", ".bbbbbb.", "abbbbbba", "abbbbbba",
    "abbbbbba", "abbbbbba", ".bbbbbb.", ".ll..ll.", ".ll..ll.", ".ll..ll.", ".ss..ss.", ".ss..ss.",
]


def scene_body(cfg, model, accent, world, dz, projects, step_class):
    cam = Cam(dz)
    P = cam.P
    rng = random.Random(5)
    bright = mix(accent, "#ffffff", 0.6)
    body = []

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
    far = []
    x = CX - 40
    while x < CX + 40:
        w = rng.randrange(6, 14) // 2 * 2
        h = rng.randrange(14, 42) // 2 * 2
        far.append(rect_d(x, HY - h, w, h + 8))
        x += w
    body.append(path("".join(far), "#0b1230"))

    zfar = dz + 78
    road = [P(-ROAD, 0, dz + ZMIN), P(-ROAD, 0, zfar), P(ROAD, 0, zfar), P(ROAD, 0, dz + ZMIN)]
    body.append(rects(0, HY, SW, SH - HY, R.GROUND))
    body.append(path(poly(road), R.PAVE))
    for side in (-1, 1):
        walk = [P(side * ROAD, 0, dz + ZMIN), P(side * ROAD, 0, zfar), P(side * HALF, 0, zfar), P(side * HALF, 0, dz + ZMIN)]
        curb = [P(side * ROAD, 0, dz + ZMIN), P(side * ROAD, 0, zfar), P(side * (ROAD + 0.25), 0, zfar), P(side * (ROAD + 0.25), 0, dz + ZMIN)]
        body.append(path(poly(walk), "#18204a") + path(poly(curb), "#2a3668"))
    dashes, z = [], 7.0
    while z < ZW:
        if z - dz > 5 and z - dz < 76:
            dashes.append(poly([P(-0.12, 0, z), P(-0.12, 0, z + 1.6), P(0.12, 0, z + 1.6), P(0.12, 0, z)]))
        z += 4.5
    body.append(path("".join(dashes), "#2e3a6e"))

    walls, roofs, offs, ons, hots = [], [], {}, [], []
    for b in world:
        if b["z1"] - dz <= ZMIN + 0.3 or b["z0"] - dz > 80:
            continue
        z0 = max(b["z0"], dz + ZMIN)
        zc = (z0 + b["z1"]) / 2
        base = R.WALL_A if b["alt"] == 0 else R.WALL_B
        walls.append((cam.fog(base, zc), cam.wall(b["side"], z0, b["z1"] - 0.15, 0, b["h"])))
        roofs.append((cam.fog("#2a3668", zc), cam.wall(b["side"], z0, b["z1"] - 0.15, b["h"] - 0.5, b["h"])))
        for za, zb, ya, yb, state in b["wins"]:
            if za - dz < ZMIN + 0.2:
                continue
            pts = cam.wall(b["side"], za, zb, ya, yb)
            xs = [p[0] for p in pts]
            if max(xs) - min(xs) < 1.2:
                continue
            if state == 2:
                hots.append(poly(pts))
            elif state == 1:
                ons.append(poly(pts))
            else:
                offs.setdefault(cam.fog(R.WINDOW_OFF, zc), []).append(poly(pts))
    for color, pts in walls:
        body.append(path(poly(pts), color))
    body.append("".join(path(poly(p), c) for c, p in roofs))
    for color, polys in offs.items():
        body.append(path("".join(polys), color))
    body.append(path("".join(ons), accent) + path("".join(hots), bright))

    # Türen mit Namensschild
    for (side, z), proj in zip(DOORS, projects):
        r = z - dz
        if r < ZMIN + 2 or r > 70:
            continue
        door = cam.wall(side, z + 0.4, z + 2.8, 0, 2.7)
        frame = cam.wall(side, z + 0.2, z + 3.0, 0, 2.9)
        body.append(path(poly(frame), mix(accent, "#000000", 0.35)))
        body.append(path(poly(door), "#06091a"))
        glow = cam.wall(side, z + 0.6, z + 2.6, 0.1, 2.5)
        body.append(f'<path d="{poly(glow)}" fill="{accent}" fill-opacity=".10"/>')
        name = R.truncate_px(proj["name"], 190, 2)
        tw = max(R.pf.width(name, 2), R.pf.width(tr(cfg, "enter"), 2)) + 20
        bw, bh = tw, 46
        wm = 3.2
        scale = (F * wm / r) / bw
        xin = side * HALF + 1.4 if side < 0 else side * HALF - wm - 1.4
        sx, sy = P(xin, 5.2, z)
        g = [R.rects(0, 0, bw, bh, R.BOARD), R.rects(0, 0, bw, 2, accent), R.rects(0, bh - 2, bw, 2, accent),
             R.rects(0, 0, 2, bh, accent), R.rects(bw - 2, 0, 2, bh, accent),
             R.tpath(name, 10, 10, 2, bright), R.tpath(tr(cfg, "enter") if proj.get("url") else tr(cfg, "soon"), 10, 28, 2, accent)]
        body.append(f'<g transform="translate({sx:.1f} {sy:.1f}) scale({scale:.3f})">{"".join(g)}</g>')

    # Laternen
    lamp = []
    for side, z in ((-1, 7), (1, 11), (-1, 16), (1, 24), (-1, 34), (1, 48), (-1, 60), (1, 72), (-1, 84), (1, 96)):
        r = z - dz
        if r < ZMIN + 1 or r > 78:
            continue
        x = side * (ROAD + 0.9)
        bx, by = P(x, 0, z)
        tx, ty = P(x, 5.4, z)
        wpx = max(2, int(F * 0.18 / r) // 2 * 2)
        lamp.append(rects(int(bx) - wpx // 2, int(ty), wpx, int(by - ty), "#2a3668"))
        hx, hy = P(x - side * 0.9, 5.5, z)
        lamp.append(rects(int(min(hx, tx)), int(ty) - wpx, int(abs(hx - tx)) + wpx, wpx, "#2a3668"))
        hr = max(3, int(F * 0.45 / r))
        lamp.append(f'<path d="{rect_d(int(hx) - hr, int(hy) - hr // 2, hr * 2, hr)}" fill="{bright}"/>')
        lamp.append(f'<path d="{rect_d(int(hx) - hr * 2, int(hy) - hr, hr * 4, hr * 2)}" fill="{accent}" fill-opacity=".10"/>')
        pool = poly([P(x - 2.4, 0, max(z - 1.4, dz + ZMIN)), P(x + 2.4, 0, max(z - 1.4, dz + ZMIN)), P(x + 2.4, 0, z + 1.8), P(x - 2.4, 0, z + 1.8)])
        lamp.append(f'<path d="{pool}" fill="{accent}" fill-opacity=".07"/>')
    body.append("".join(lamp))

    # Leuchtreklamen mit den Zahlen
    signs = [
        (fmt_int(cfg, model["year_total"]), tr(cfg, "sign_year")),
        (fmt_int(cfg, model["active_days"]), tr(cfg, "sign_days")),
        (fmt_int(cfg, model["longest"]), tr(cfg, "sign_streak")),
        (fmt_int(cfg, model["total"]), tr(cfg, "sign_total")),
    ]
    spots = [(-1, 12.0), (1, 19.0), (-1, 36.0), (1, 44.0)]
    sw_, sh_ = 152, 64
    placed = []
    for k, ((num, label), (side, z)) in enumerate(zip(signs, spots)):
        r = z - dz
        if r < 6 or r > 60:
            continue
        wm = 3.4
        scale = (F * wm / r) / sw_
        x_in = side * (HALF - wm) if side > 0 else -HALF
        sx, sy = P(x_in, 9.0, z)
        g = (f'<g transform="translate({sx:.1f} {sy:.1f}) scale({scale:.3f})">'
             f'{R.sign_board(0, 0, sw_, sh_, num, label, accent, round(k * 1.7, 1))}</g>')
        placed.append((z, g))
    body.append("".join(g for _, g in sorted(placed, key=lambda t: -t[0])))

    return f'<g class="{step_class}">{"".join(body)}</g>'


def figure():
    px = 4
    pw, ph = 8 * px, len(PERSON) * px
    fig = sprite(PERSON, {"h": "#3a4784", "b": "#2a3668", "a": "#222c58", "l": "#161d3e", "s": "#05070f"},
                 CX - pw // 2, SH - ph - 10, px)
    return (rects(CX - pw // 2 - 6, SH - 10, pw + 12, 4, "#05070f", 'fill-opacity=".5"') + fig
            + rects(CX - pw // 2, SH - ph - 10 + 3 * px, px, px * 2, "#9fb0e8", 'fill-opacity=".5"'))


def slice_doc(body, x0, w, h=SH):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="{x0} 0 {w} {h}"'
            f' shape-rendering="crispEdges"><style>{R.CSS}</style>{body}</svg>\n')


def strip_doc(cfg, text, w, accent):
    h = 44
    tw = R.pf.width(text, 2)
    body = (rects(0, 0, w, h, "#0a0f22") + rects(0, 0, w, 2, "#2a3668") + rects(0, h - 2, w, 2, "#2a3668")
            + R.tpath(text, (w - tw) // 2, 15, 2, accent))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"'
            f' shape-rendering="crispEdges"><style>{R.CSS}</style>{body}</svg>\n'), h


# ---------------------------------------------------------------- Räume

def room_doc(cfg, proj, accent, index):
    W, H = SW, 440
    bright = mix(accent, "#ffffff", 0.45)
    soon = bool(proj.get("coming_soon"))
    b = [rects(0, 0, W, H, "#0e1530"), rects(0, 330, W, H - 330, "#0a0f22"), rects(0, 328, W, 4, "#2a3668")]
    # Bodenlinien
    for k in range(-8, 9):
        b.append(f'<path d="M{CX + k * 22} 332 L{CX + k * 80} {H}" stroke="#18204a" stroke-width="2" fill="none"/>')
    # Fenster mit Nachtstadt
    wx, wy, ww, wh = 40, 70, 190, 170
    b.append(rects(wx - 6, wy - 6, ww + 12, wh + 12, "#2a3668"))
    b.append(rects(wx, wy, ww, wh, "#0b1230"))
    rr = random.Random(index + 3)
    x = wx
    while x < wx + ww:
        w = rr.randrange(14, 30) // 2 * 2
        h = rr.randrange(30, 100) // 2 * 2
        w = min(w, wx + ww - x)
        b.append(rects(x, wy + wh - h, w, h, "#18204a"))
        for wy2 in range(wy + wh - h + 6, wy + wh - 6, 10):
            if rr.random() < 0.35:
                b.append(rects(x + 4, wy2, 4, 4, accent))
        x += w
    b.append(rects(wx + ww // 2 - 3, wy, 6, wh, "#2a3668"))
    b.append(R.moon(wx + 150, wy + 36, 10))
    # Lampe
    b.append(rects(CX - 1, 0, 2, 40, "#2a3668"))
    b.append(rects(CX - 26, 40, 52, 10, "#2a3668"))
    b.append(f'<path d="M{CX - 24} 50 L{CX + 24} 50 L{CX + 120} 330 L{CX - 120} 330Z" fill="{accent}" fill-opacity=".06"/>')
    b.append(rects(CX - 20, 50, 40, 4, bright))

    name = R.truncate_px(proj["name"], 380, 3)
    desc = R.wrap_px(proj.get("description") or tr(cfg, "no_desc"), 380, 2, 3)
    nx = 300
    b.append(f'<g class="fl"><g opacity=".25">{path(R.pf.halo_d(name, nx, 80, 3, 1), accent)}</g>{R.tpath(name, nx, 80, 3, bright)}</g>')
    for i, line in enumerate(desc):
        b.append(R.tpath(line, nx, 130 + i * 22, 2, "#aab6ee"))

    if soon:
        # Baustelle: Absperrband und Kisten
        for k in range(0, W, 28):
            b.append(rects(k, 300, 14, 12, "#ffd166") + rects(k + 14, 300, 14, 12, "#0a0f22"))
        b.append(rects(300, 262, 70, 38, "#2a3668") + rects(310, 252, 50, 10, "#3a4784"))
        b.append(rects(400, 276, 50, 24, "#2a3668"))
        label = tr(cfg, "construction")
        b.append(R.tpath(label, nx, 200, 2, accent))
    else:
        # Schreibtisch mit Bildschirm
        b.append(rects(280, 300, 280, 14, "#2a3668") + rects(292, 314, 8, 40, "#1b2549") + rects(540, 314, 8, 40, "#1b2549"))
        b.append(rects(370, 218, 100, 70, "#2a3668") + rects(374, 222, 92, 62, "#06091a") + rects(414, 288, 12, 12, "#2a3668"))
        lines = []
        if proj.get("language"):
            lines.append(proj["language"])
        lines.append(f"★ {proj.get('stars', 0)}")
        if proj.get("pushed"):
            try:
                lines.append(R.fmt_date(cfg, R.parse_date(proj["pushed"]), with_year=False))
            except ValueError:
                pass
        for i, ln in enumerate(lines[:3]):
            b.append(R.tpath(R.truncate_px(ln, 84, 2), 380, 228 + i * 16, 2, "#aab6ee" if i else accent))
        b.append(f'<g class="tw">{R.tpath(tr(cfg, "open_repo"), nx, 200, 2, bright)}</g>')
    # Tür zurück
    b.append(rects(W - 130, 150, 80, 180, "#2a3668") + rects(W - 124, 156, 68, 174, "#06091a"))
    b.append(rects(W - 70, 245, 6, 6, bright))
    b.append(R.tpath(tr(cfg, "exit"), W - 130, 120, 2, accent))
    alt = tr(cfg, "alt_room").format(name=proj["name"], desc=" ".join(desc))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img"'
            f' aria-label="{R.esc(alt)}" shape-rendering="crispEdges"><style>{R.CSS}</style>{"".join(b)}</svg>\n'), H, alt


# ---------------------------------------------------------------- Zusammenbau

def build_game(cfg, model, accent, projects, user, emit):
    """Erzeugt alle Bilder (über emit) und liefert die Seitenbeschreibung für readme.py."""
    world = build_world(model)
    base = f"https://github.com/{user}/{user}/blob/main/"
    profile = f"https://github.com/{user}"
    ps = (projects + [{"name": "", "description": "", "url": None, "coming_soon": True}] * 4)[:4]

    def page_path(step):
        return f"assets/street/{step}.md"

    def page_url(step):
        return base + page_path(step)

    pages = []
    n = len(STEPS)
    door_step = {1: (0, 1), 2: (2, 3)}
    alt_street = tr(cfg, "alt_street").format(
        year=fmt_int(cfg, model["year_total"]), days=fmt_int(cfg, model["active_days"]),
        streak=fmt_int(cfg, model["longest"]), total=fmt_int(cfg, model["total"]))
    for step, dz in enumerate(STEPS):
        cls = "zoom" if step == 0 else "walk"
        body = scene_body(cfg, model, accent, world, dz, ps, cls) + figure()
        hint = tr(cfg, "hint_walk") if step < n - 1 else tr(cfg, "hint_end")
        hx = CX - R.pf.width(hint, 2) // 2
        body += (f'<g class="tw" style="animation-duration:2.6s">{rects(hx - 10, SH - 150, R.pf.width(hint, 2) + 20, 24, "#0a0f22", "fill-opacity=" + chr(34) + ".55" + chr(34))}'
                 f'{R.tpath(hint, hx, SH - 143, 2, accent)}</g>')
        left_i, right_i = door_step.get(step, (None, None))
        row = []
        spans = [(0, CUTS[0]), (CUTS[0], CUTS[1] - CUTS[0]), (CUTS[1], SW - CUTS[1])]
        hrefs = [None, None, None]
        if left_i is not None:
            hrefs[0] = base + f"assets/street/room-{left_i + 1}.md"
            hrefs[2] = base + f"assets/street/room-{right_i + 1}.md"
        if step < n - 1:
            hrefs[1] = page_url(step + 1)
        for k, (x0, w) in enumerate(spans):
            item = emit(f"walk-{step}-{k}.svg", (slice_doc(body, x0, w), SH, alt_street), hrefs[k], w)
            item["pct"] = round(w / SW * 100, 4)
            row.append(item)
        rows = [row]
        strips = []
        s1, h1 = strip_doc(cfg, tr(cfg, "leave"), SW // 2, accent)
        strips.append(emit("strip-leave.svg", (s1, h1, tr(cfg, "leave")), profile, SW // 2))
        if step > 0:
            s2, h2 = strip_doc(cfg, tr(cfg, "back_step"), SW // 2, accent)
            strips.append(emit("strip-back.svg", (s2, h2, tr(cfg, "back_step")), page_url(step - 1), SW // 2))
        rows.append(strips)
        pages.append({"path": page_path(step), "rows": rows})

    # Räume
    door_back = {0: 1, 1: 1, 2: 2, 3: 2}
    for i, proj in enumerate(ps):
        content, h, alt = room_doc(cfg, proj, accent, i)
        item = emit(f"room-{i + 1}.svg", (content, h, alt), proj.get("url"), SW)
        s, sh = strip_doc(cfg, tr(cfg, "back_street"), SW, accent)
        back = emit("strip-room-back.svg", (s, sh, tr(cfg, "back_street")), None, SW)
        pages.append({"path": f"assets/street/room-{i + 1}.md", "rows": [[item], [dict(back, href=page_url(door_back[i]))]]})
    return pages
