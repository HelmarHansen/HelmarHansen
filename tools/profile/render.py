#!/usr/bin/env python3
"""Zeichnet das Profil als Pixel-Nacht: Sternbild-Name, Stadt aus deinen Wochen, Schilder als Projekte.

GitHub erlaubt in READMEs kein CSS und kein JavaScript, aber ein per <img> eingebundenes SVG darf
eigenes CSS samt Animationen enthalten. Der Text ist aus Rechtecken gezeichnet (pixelfont.py),
dadurch wird keine Schriftdatei geladen.

Die Stadt: ein Gebäude pro Woche. Die Höhe folgt den Beiträgen der Woche, die Zahl der
beleuchteten Fenster entspricht den aktiven Tagen. Welches Fenster leuchtet, ist per festem Seed
bestimmt, damit sich das Bild ohne neue Daten nicht ändert.
"""
import datetime
import json
import math
import os
import random
import sys

import pixelfont as pf
from common import (
    ASSET_DIR, CONFIG_PATH, DATA_PATH, MANIFEST_PATH, esc, fmt_date, fmt_int,
    load_json, parse_date, tr, write_if_changed,
)

W = 830
STREET_Y = 470          # Oberkante des Gehwegs, hier stehen die Gebäude
SCENE_H = 494
PITCH = 14              # Breite eines Gebäudes (eine Woche)
MIN_H, MAX_H = 40, 118

SKY = ["#060a18", "#09102a", "#0d1637", "#131d44", "#1b2755"]
SKY_STOPS = [0, 110, 200, 290, 380]
FAR_1, FAR_2 = "#0b1230", "#0e1636"
WALL_A, WALL_B, ROOF = "#161f3f", "#1b2549", "#2a3668"
WINDOW_OFF = "#0e1530"
PAVE, CURB, GROUND = "#0e1224", "#1c2547", "#131a35"
BOARD, BOARD_EDGE = "#0a0f22", "#2a3668"
TEXT, MUTED = "#e8ecff", "#8e9ac9"
STAR_COLORS = ["#9fb0e8", "#c9d3ff", "#ffffff"]
RED = "#ff6b4a"

CSS = """
.fade{animation:fade .9s both}
@keyframes fade{from{opacity:0}}
.tw{animation:tw 3.2s steps(1) infinite both}
@keyframes tw{0%,100%{opacity:1}50%{opacity:.25}}
.bl{animation:bl 2.4s steps(1) infinite both}
@keyframes bl{0%,60%{opacity:1}61%,100%{opacity:0}}
.fl{animation:fl 6s steps(1) infinite both}
@keyframes fl{0%,91%,95%,100%{opacity:1}93%,97%{opacity:.4}}
.p1,.p2,.p3,.p4{animation-duration:48s;animation-iteration-count:infinite;animation-direction:normal}
.p0{animation:p0 48s steps(2) infinite}@keyframes p0{0%,100%{transform:translateX(-1px)}50%{transform:translateX(1px)}}
.p1{animation-name:p1;animation-timing-function:steps(6)}@keyframes p1{0%,100%{transform:translateX(-3px)}50%{transform:translateX(3px)}}
.p2{animation-name:p2;animation-timing-function:steps(12)}@keyframes p2{0%,100%{transform:translateX(-6px)}50%{transform:translateX(6px)}}
.p3{animation-name:p3;animation-timing-function:steps(24)}@keyframes p3{0%,100%{transform:translateX(-12px)}50%{transform:translateX(12px)}}
.cl{animation:cl linear infinite}
@keyframes cl{from{transform:translateX(-260px)}to{transform:translateX(900px)}}
.pl{animation:pl 52s steps(500) infinite}
@keyframes pl{0%,55%{transform:translateX(-40px)}100%{transform:translateX(900px)}}
.ss{animation:ss 17s steps(14) infinite;opacity:0}
@keyframes ss{0%,88%{transform:translate(0,0);opacity:0}89%{opacity:1}100%{transform:translate(110px,60px);opacity:0}}
.c1{animation:c1 19s steps(430) infinite}
@keyframes c1{from{transform:translateX(-30px)}to{transform:translateX(860px)}}
.c2{animation:c2 27s steps(430) infinite}
@keyframes c2{from{transform:translateX(860px)}to{transform:translateX(-30px)}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
"""


# ---------------------------------------------------------------- Hilfen

def mix(hex_a, hex_b, t):
    a = [int(hex_a[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(hex_b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def rect_d(x, y, w, h):
    return f"M{x:g} {y:g}h{w:g}v{h:g}h-{w:g}z"


def rects(x, y, w, h, fill, extra=""):
    return f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" fill="{fill}" {extra}/>'


def path(d, fill, extra=""):
    return f'<path d="{d}" fill="{fill}" {extra}/>' if d else ""


def tpath(s, x, y, scale, fill, extra=""):
    return path(pf.path_d(s, x, y, scale), fill, extra)


def svg_doc(w, h, label, body):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"'
        f' role="img" aria-label="{esc(label)}" shape-rendering="crispEdges">'
        f"<style>{CSS}</style>{body}</svg>\n"
    )


def truncate_px(text, maxw, scale):
    text = " ".join(str(text).split())
    if pf.width(text, scale) <= maxw:
        return text
    while text and pf.width(text + "…", scale) > maxw:
        text = text[:-1]
    return text.rstrip() + "…"


def wrap_px(text, maxw, scale, max_lines):
    words = " ".join(str(text).split()).split(" ")
    lines, cur = [], ""
    for i, w_ in enumerate(words):
        trial = f"{cur} {w_}".strip()
        if pf.width(trial, scale) <= maxw:
            cur = trial
            continue
        if cur:
            lines.append(cur)
        cur = w_
        if len(lines) == max_lines:
            break
    else:
        if cur:
            lines.append(cur)
    lines = lines[:max_lines]
    if " ".join(lines) != " ".join(words) and lines:
        lines[-1] = truncate_px(lines[-1] + " …", maxw, scale).replace(" …", "…")
    return [truncate_px(ln, maxw, scale) for ln in lines]


# ---------------------------------------------------------------- Datenmodell

def build_model(data):
    today = parse_date(data["updated"])
    days = {parse_date(k): v for k, v in data["days"].items()}
    last_monday = today - datetime.timedelta(days=today.weekday())
    start = last_monday - datetime.timedelta(weeks=52)
    weeks = []
    for c in range(53):
        col = []
        for r in range(7):
            d = start + datetime.timedelta(days=c * 7 + r)
            col.append((d, days.get(d, 0) if d <= today else None))
        weeks.append(col)
    weekly = [sum(v for _, v in col if v) for col in weeks]
    win_start = today - datetime.timedelta(days=364)
    in_window = {d: v for d, v in days.items() if win_start <= d <= today}
    longest = run = 0
    if days:
        d = min(days)
        while d <= today:
            run = run + 1 if days.get(d, 0) > 0 else 0
            longest = max(longest, run)
            d += datetime.timedelta(days=1)
    return {
        "today": today,
        "weeks": weeks,
        "weekly": weekly,
        "year_total": sum(in_window.values()),
        "active_days": sum(1 for v in in_window.values() if v > 0),
        "longest": longest,
        "total": sum(days.values()),
        "counts": sorted(v for v in in_window.values() if v > 0),
    }


# ---------------------------------------------------------------- Sternbild-Schrift
# Jeder Buchstabe: Linienzüge auf einem Raster von 4 x 6 Zellen.
STROKES = {
    "A": [[(0, 6), (2, 0), (4, 6)], [(0.67, 4), (3.33, 4)]],
    "B": [[(0, 0), (0, 6)], [(0, 0), (3, 0), (4, 1), (3, 3), (0, 3)], [(3, 3), (4, 4), (4, 5), (3, 6), (0, 6)]],
    "C": [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 5), (1, 6), (3, 6), (4, 5)]],
    "D": [[(0, 0), (0, 6), (2, 6), (4, 4), (4, 2), (2, 0), (0, 0)]],
    "E": [[(4, 0), (0, 0), (0, 6), (4, 6)], [(0, 3), (3, 3)]],
    "F": [[(4, 0), (0, 0), (0, 6)], [(0, 3), (3, 3)]],
    "G": [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 5), (1, 6), (3, 6), (4, 5), (4, 3), (2, 3)]],
    "H": [[(0, 0), (0, 6)], [(4, 0), (4, 6)], [(0, 3), (4, 3)]],
    "I": [[(1, 0), (3, 0)], [(2, 0), (2, 6)], [(1, 6), (3, 6)]],
    "J": [[(4, 0), (4, 4.5), (3, 6), (1, 6), (0, 4.5)]],
    "K": [[(0, 0), (0, 6)], [(4, 0), (0, 3), (4, 6)]],
    "L": [[(0, 0), (0, 6), (4, 6)]],
    "M": [[(0, 6), (0, 0), (2, 3), (4, 0), (4, 6)]],
    "N": [[(0, 6), (0, 0), (4, 6), (4, 0)]],
    "O": [[(1, 0), (3, 0), (4, 1), (4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0)]],
    "P": [[(0, 6), (0, 0), (3, 0), (4, 1), (4, 2), (3, 3), (0, 3)]],
    "Q": [[(1, 0), (3, 0), (4, 1), (4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0)], [(2, 4), (4, 6)]],
    "R": [[(0, 6), (0, 0), (3, 0), (4, 1), (4, 2), (3, 3), (0, 3)], [(2, 3), (4, 6)]],
    "S": [[(4, 1), (3, 0), (1, 0), (0, 1), (0, 2), (1, 3), (3, 3), (4, 4), (4, 5), (3, 6), (1, 6), (0, 5)]],
    "T": [[(0, 0), (4, 0)], [(2, 0), (2, 6)]],
    "U": [[(0, 0), (0, 5), (1, 6), (3, 6), (4, 5), (4, 0)]],
    "V": [[(0, 0), (2, 6), (4, 0)]],
    "W": [[(0, 0), (1, 6), (2, 3), (3, 6), (4, 0)]],
    "X": [[(0, 0), (4, 6)], [(4, 0), (0, 6)]],
    "Y": [[(0, 0), (2, 3), (4, 0)], [(2, 3), (2, 6)]],
    "Z": [[(0, 0), (4, 0), (0, 6), (4, 6)]],
}


def bresenham(x0, y0, x1, y1):
    pts = []
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        pts.append((x0, y0))
        if x0 == x1 and y0 == y1:
            return pts
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def constellation(name, x0, y0, accent, rng):
    """Name als Punktwolke: Sterne unterschiedlicher Größe liegen dicht entlang der Buchstaben."""
    letters = [c for c in name.upper()]
    n_cells = sum(5 if c in STROKES else 2 for c in letters) - 1
    cell = int(min(16, max(8, ((W - x0 - 150) / max(n_cells, 1)) // 2 * 2)))
    dust, mid, bright, warm, halo = [], [], [], [], []
    twinkle = []
    seen = set()

    def put(x, y, kind):
        x, y = int(x) // 2 * 2, int(y) // 2 * 2
        if (x, y) in seen:
            return
        seen.add((x, y))
        if kind == 0:
            dust.append(rect_d(x, y, 2, 2))
        elif kind == 1:
            mid.append(rect_d(x, y, 2, 2))
        else:
            plus = (rect_d(x, y, 2, 2) + rect_d(x - 2, y, 2, 2) + rect_d(x + 2, y, 2, 2)
                    + rect_d(x, y - 2, 2, 2) + rect_d(x, y + 2, 2, 2))
            halo.append(rect_d(x - 4, y - 4, 10, 10))
            if kind == 3:
                warm.append(plus)
            elif rng.random() < 0.35:
                twinkle.append((plus, round(rng.random() * 3, 1)))
            else:
                bright.append(plus)

    cx = x0
    for ch in letters:
        if ch not in STROKES:
            cx += 2 * cell
            continue
        for stroke in STROKES[ch]:
            for a, b in zip(stroke, stroke[1:]):
                ax, ay = cx + a[0] * cell, y0 + a[1] * cell
                bx, by = cx + b[0] * cell, y0 + b[1] * cell
                length = math.hypot(bx - ax, by - ay)
                steps = max(1, int(length / 2.5))
                for k in range(steps + 1):
                    t = k / steps
                    px = ax + (bx - ax) * t + rng.uniform(-1.5, 1.5)
                    py = ay + (by - ay) * t + rng.uniform(-1.5, 1.5)
                    r = rng.random()
                    put(px, py, 0 if r < 0.2 else 1 if r < 0.9 else 2 if r < 0.975 else 3)
        # Staub rund um den Buchstaben
        for _ in range(14):
            put(cx - 8 + rng.random() * (4 * cell + 16), y0 - 8 + rng.random() * (6 * cell + 16), 0)
        cx += 5 * cell
    out = [path("".join(halo), "#9fb0e8", 'fill-opacity=".09"'), path("".join(dust), "#5a6aa6"),
           path("".join(mid), "#c4cffa"), path("".join(bright), "#ffffff"), path("".join(warm), accent)]
    for d, delay in twinkle:
        out.append(path(d, "#ffffff", f'class="tw" style="animation-delay:{delay}s"'))
    height = 6 * cell
    return f'<g class="fade" style="animation-delay:.3s">{"".join(out)}</g>', height


# ---------------------------------------------------------------- Himmel und Stadt

def sky_bands():
    out = []
    for i, color in enumerate(SKY):
        y0 = SKY_STOPS[i]
        y1 = SKY_STOPS[i + 1] if i + 1 < len(SKY) else STREET_Y
        out.append(rects(0, y0, W, y1 - y0, color))
    # Übergänge aus zwei Reihen Schachbrett, wie bei alter Pixelgrafik
    for i in range(1, len(SKY)):
        y = SKY_STOPS[i]
        d = []
        for row, yy in enumerate((y - 4, y - 2)):
            for x in range(0, W, 4):
                d.append(rect_d(x + (2 if row else 0), yy, 2, 2))
        out.append(path("".join(d), SKY[i]))
    return "".join(out)


def stars_bg(rng, avoid):
    small, plus, dim = [], [], []
    tries = 0
    while len(small) + len(plus) < 95 and tries < 600:
        tries += 1
        x, y = rng.randrange(4, W - 4) // 2 * 2, rng.randrange(6, 340) // 2 * 2
        if any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in avoid):
            continue
        r = rng.random()
        if r < 0.12:
            plus.append(rect_d(x, y, 2, 2) + rect_d(x - 2, y, 2, 2) + rect_d(x + 2, y, 2, 2)
                        + rect_d(x, y - 2, 2, 2) + rect_d(x, y + 2, 2, 2))
        elif r < 0.55:
            small.append(rect_d(x, y, 2, 2))
        else:
            dim.append(rect_d(x, y, 2, 2))
    # einige Sterne funkeln
    tw = []
    for _ in range(9):
        x, y = rng.randrange(4, W - 4) // 2 * 2, rng.randrange(6, 300) // 2 * 2
        if any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in avoid):
            continue
        tw.append(f'<path d="{rect_d(x, y, 2, 2)}" fill="#ffffff" class="tw" style="animation-delay:{round(rng.random() * 3, 1)}s"/>')
    return (path("".join(dim), "#5a6aa6") + path("".join(small), "#aab6ee") + path("".join(plus), "#ffffff")
            + "".join(tw))


def moon(cx, cy, r=22):
    d = []
    for y in range(cy - r, cy + r, 2):
        for x in range(cx - r, cx + r, 2):
            mx, my = x + 1 - cx, y + 1 - cy
            if mx * mx + my * my <= r * r and (mx - 9) ** 2 + (my + 5) ** 2 > (r * 0.92) ** 2:
                d.append(rect_d(x, y, 2, 2))
    return path("".join(d), "#f6efd0")


def wisps():
    out = []
    for k, (y, dur, delay, w) in enumerate(((170, 90, 0, 150), (236, 130, 40, 210), (300, 70, 20, 120))):
        r = random.Random(77 + k)
        d, rowx = [], 0
        for row in range(3):
            ww = w - row * 28 - r.randrange(0, 20)
            ww = ww // 2 * 2
            d.append(rect_d(row * 14, y + row * 2, ww, 2))
        out.append(f'<g class="cl" style="animation-duration:{dur}s;animation-delay:-{delay}s">'
                   f'{path("".join(d), "#9fb0e8", chr(102) + "ill-opacity=" + chr(34) + ".07" + chr(34))}</g>')
    return "".join(out)


def plane(y=96):
    body = (rects(0, y, 14, 2, "#8e9ac9") + rects(4, y - 4, 4, 4, "#6b78ad") + rects(4, y + 2, 4, 4, "#6b78ad")
            + rects(12, y - 2, 2, 2, "#6b78ad")
            + f'<path d="{rect_d(-2, y, 2, 2)}" fill="{RED}" class="bl"/>'
            + f'<path d="{rect_d(5, y - 4, 2, 2)}" fill="#ffffff" class="tw" style="animation-duration:1.6s"/>')
    return f'<g class="pl">{body}</g>'


def shooting_star(x=470, y=40):
    d = "".join(rect_d(x - i * 4, y - i * 2, 2, 2) for i in range(1, 6))
    return (f'<g class="ss"><g opacity=".35">{path(d, "#c9d3ff")}</g>'
            f'{rects(x, y, 4, 2, "#ffffff")}</g>')


def car(y, color, dirn, cls):
    head = "#ffe9a8" if dirn > 0 else RED
    tail = RED if dirn > 0 else "#ffe9a8"
    hx = 10 if dirn > 0 else 0
    tx = 0 if dirn > 0 else 10
    body = (rects(0, y, 12, 4, color) + rects(2, y - 2, 8, 2, color)
            + rects(4, y - 2, 4, 2, "#aab6ee") + rects(hx, y, 2, 2, head) + rects(tx, y, 2, 2, tail)
            + rects(1, y + 4, 3, 2, "#05070f") + rects(8, y + 4, 3, 2, "#05070f"))
    glow = rects(hx + (2 if dirn > 0 else -8), y, 8, 2, head, 'fill-opacity=".18"')
    return f'<g class="{cls}">{body}{glow}</g>'


def far_skyline(rng):
    out = []
    for color, lo, hi, seed in ((FAR_1, 50, 118, 1), (FAR_2, 36, 96, 2)):
        r = random.Random(seed + 10)
        x, d = -30 - r.randrange(0, 10), []
        while x < W + 30:
            w = r.randrange(12, 28) // 2 * 2
            h = r.randrange(lo, hi) // 2 * 2
            d.append(rect_d(x, STREET_Y - h, w, h))
            x += w
        out.append(f'<g class="{"p1" if color == FAR_1 else "p2"}">{path("".join(d), color)}</g>')
    return "".join(out)


def build_city(model, accent, sign_roofs):
    weekly = model["weekly"]
    maxw = max(weekly + [1])
    counts = model["counts"]
    q75 = counts[int(len(counts) * 0.75)] if counts else 1
    bright = mix(accent, "#ffffff", 0.6)
    x0 = (W - 53 * PITCH) // 2
    walls = {WALL_A: [], WALL_B: []}
    roofs, off, on, hot, ant, lights = [], [], [], [], [], []
    side_s, top_s = ([[], []], [[], []])
    heights = []
    for i, col in enumerate(model["weeks"]):
        h = int(round(MIN_H + (MAX_H - MIN_H) * math.sqrt(weekly[i] / maxw))) // 2 * 2
        heights.append(h)
    BW = PITCH - 4      # Frontbreite; 4 px Tiefe nach rechts oben
    for i, col in enumerate(model["weeks"]):
        bx, h = x0 + i * PITCH, heights[i]
        top = STREET_Y - h
        k = i % 2
        walls[WALL_A if k == 0 else WALL_B].append(rect_d(bx, top, BW, h))
        side_s[k].append(rect_d(bx + BW, top - 2, 2, h + 2) + rect_d(bx + BW + 2, top - 4, 2, h + 4))
        top_s[k].append(rect_d(bx + 2, top - 2, BW, 2) + rect_d(bx + 4, top - 4, BW, 2))
        roofs.append(rect_d(bx, top, BW, 2))
        rows = (h - 6) // 8
        slots = list(range(rows * 2))
        random.Random(col[0][0].toordinal()).shuffle(slots)
        active = [(d, v) for d, v in col if v]
        lit = {}
        for n, (_, v) in enumerate(active):
            lit[slots[n]] = v
        for s_ in range(rows * 2):
            wx = bx + 1 + (s_ % 2) * 5
            wy = STREET_Y - 10 - (s_ // 2) * 8
            if s_ in lit:
                (hot if lit[s_] >= q75 else on).append(rect_d(wx, wy, 3, 4))
            else:
                off.append(rect_d(wx, wy, 3, 4))
        if weekly[i] >= 0.88 * maxw and weekly[i] > 0 and i not in sign_roofs:
            ant.append(rect_d(bx + 6, top - 12, 2, 10))
            lights.append(f'<path d="{rect_d(bx + 6, top - 14, 2, 2)}" fill="{RED}" class="bl" style="animation-delay:{round((i % 5) * 0.4, 1)}s"/>')
    body = ""
    for k, c in enumerate((WALL_A, WALL_B)):
        body += path("".join(side_s[k]), mix(c, "#000000", 0.45))
        body += path("".join(top_s[k]), mix(c, "#9fb0e8", 0.28))
    body += "".join(path("".join(d), c) for c, d in walls.items())
    body += path("".join(roofs), ROOF) + path("".join(ant), ROOF) + "".join(lights)
    blink = []
    steady = []
    for n, d_ in enumerate(on):
        if n % 11 == 5:
            blink.append(f'<path d="{d_}" fill="{accent}" class="tw" style="animation-delay:{round((n % 7) * 0.9, 1)}s;animation-duration:{5 + n % 4}s"/>')
        else:
            steady.append(d_)
    body += path("".join(off), WINDOW_OFF) + path("".join(steady), accent) + "".join(blink) + path("".join(hot), bright)
    return body, heights, x0


def sign_board(x, y, w, h, number, label, accent, delay):
    bright = mix(accent, "#ffffff", 0.55)
    nw = pf.big_width(number, 3)
    lw = pf.width(label, 2)
    ny = y + 12
    ly = ny + 21 + 9
    parts = [
        f'<g class="fl" style="animation-delay:{delay}s">',
        rects(x + w, y - 2, 2, h + 2, mix(BOARD, "#000000", 0.4)), rects(x + w + 2, y - 4, 2, h + 2, mix(BOARD, "#000000", 0.4)),
        rects(x + 2, y - 2, w, 2, mix(accent, BOARD, 0.5)), rects(x + 4, y - 4, w, 2, mix(accent, BOARD, 0.5)),
        rects(x + w, y - 2, 4, 2, accent, 'fill-opacity=".5"'),
        rects(x - 4, y - 4, w + 8, h + 8, accent, 'fill-opacity=".10"'),
        rects(x, y, w, h, BOARD),
        rects(x, y, w, 2, accent), rects(x, y + h - 2, w, 2, accent),
        rects(x, y, 2, h, accent), rects(x + w - 2, y, 2, h, accent),
        f'<g opacity=".25">{path(pf.big_path_d(number, x + (w - nw) // 2, ny, 3, 1), accent)}</g>',
        path(pf.big_path_d(number, x + (w - nw) // 2, ny, 3), bright),
        tpath(label, x + (w - lw) // 2, ly, 2, "#aab6ee"),
        "</g>",
    ]
    return "".join(parts)


def street():
    d = [rects(0, STREET_Y, W, SCENE_H - STREET_Y, PAVE), rects(0, STREET_Y, W, 2, CURB)]
    return "".join(d)


# ---------------------------------------------------------------- Szene

def scene(cfg, model, accent):
    name = cfg.get("name", "")
    tagline = cfg.get("tagline", "")
    rng = random.Random(42)
    hi = tr(cfg, "hi")
    lines = cfg.get("config_lines", [])

    shown = lines[:3]
    text_w = max([pf.width(tagline, 2)] + [pf.width(f"{i['key']}: {i['value']}", 2) for i in shown])
    avoid = [(40, 28, max(560, 56 + text_w + 12), 62 + 96 + 24 + 26 + 22 * len(shown) + 12)]
    body = [sky_bands(),
            f'<g class="p0">{stars_bg(rng, avoid + [(W - 150, 36, W - 40, 120)])}{moon(W - 100, 74)}</g>',
            shooting_star(), wisps(), plane()]
    body.append(far_skyline(rng))

    # Texte im Himmel
    body.append(tpath(hi, 56, 34, 2, MUTED))
    star_svg, star_h = constellation(name, 60, 62, accent, rng)
    body.append(star_svg)
    ty = 62 + star_h + 24
    body.append(tpath(tagline, 56, ty, 2, TEXT))
    ly = ty + 26
    for item in shown:
        key = f"{item['key']}: "
        body.append(tpath(key, 56, ly, 2, MUTED))
        body.append(tpath(str(item["value"]), 56 + pf.width(key, 2) + 0, ly, 2, "#c9d3ff"))
        ly += 22

    # Schilder (Zahlen) planen, damit ihre Masten auf Dächern stehen
    signs = [
        (fmt_int(cfg, model["year_total"]), tr(cfg, "sign_year")),
        (fmt_int(cfg, model["active_days"]), tr(cfg, "sign_days")),
        (fmt_int(cfg, model["longest"]), tr(cfg, "sign_streak")),
        (fmt_int(cfg, model["total"]), tr(cfg, "sign_total")),
    ]
    widths = [max(pf.big_width(n, 3), pf.width(l, 2)) + 32 for n, l in signs]
    widths = [max(w, 104) for w in widths]
    gap = max((W - 88 - sum(widths)) / 3, 8)
    sx, positions = 44, []
    for w in widths:
        positions.append(int(sx))
        sx += w + gap
    heights_tmp = None
    # Gebäudehöhen vorab bestimmen (gleiche Formel wie in build_city)
    weekly = model["weekly"]
    maxw = max(weekly + [1])
    x0 = (W - 53 * PITCH) // 2
    hts = [int(round(MIN_H + (MAX_H - MIN_H) * math.sqrt(weekly[i] / maxw))) // 2 * 2 for i in range(53)]

    def building_at(px):
        return max(0, min(52, (px - x0) // PITCH))

    sign_roofs, sign_geo = set(), []
    for (num, label), sx0, w in zip(signs, positions, widths):
        p1, p2 = sx0 + 14, sx0 + w - 16
        i1, i2 = building_at(p1), building_at(p2)
        sign_roofs.update({i1, i2, building_at(p1 - 6), building_at(p2 + 6)})
        roof = min(STREET_Y - hts[i1], STREET_Y - hts[i2])
        h = 64
        sign_geo.append((sx0, roof - 24 - h, w, h, p1, p2, STREET_Y - hts[i1], STREET_Y - hts[i2]))

    city, heights, _ = build_city(model, accent, sign_roofs)
    body.append('<g class="p3">')
    body.append(city)
    for k, ((num, label), (sx0, sy, w, h, p1, p2, r1, r2)) in enumerate(zip(signs, sign_geo)):
        body.append(rects(p1, sy + h, 2, r1 - (sy + h), ROOF))
        body.append(rects(p2, sy + h, 2, r2 - (sy + h), ROOF))
        body.append(sign_board(sx0, sy, w, h, num, label, accent, round(k * 1.7, 1)))
    body.append('</g>')
    body.append(street())
    body.append(car(STREET_Y + 9, "#c94f4f", 1, "c1"))
    body.append(car(STREET_Y + 15, "#4f7ac9", -1, "c2"))

    intro = (f"{name}: {tagline}." if tagline else f"{name}.") if name else ""
    alt = tr(cfg, "alt_scene").format(
        intro=intro, year=fmt_int(cfg, model["year_total"]),
        days=fmt_int(cfg, model["active_days"]), streak=fmt_int(cfg, model["longest"]),
        total=fmt_int(cfg, model["total"]),
    )
    return svg_doc(W, SCENE_H, alt, "".join(body)), SCENE_H, alt


# ---------------------------------------------------------------- Projektschilder

PROJECT_H = 176


def project_slice(cfg, proj, w, accent):
    H = PROJECT_H
    bw, bh, by = 387, 112, 14
    bx = (w - bw) // 2
    avail = bw - 32
    bright = mix(accent, "#ffffff", 0.35)
    name = truncate_px(proj["name"], avail, 2)
    desc = wrap_px(proj["description"] or tr(cfg, "no_desc"), avail, 2, 2)
    body = [rects(0, 0, w, H, PAVE)]
    for px in (bx + 36, bx + bw - 38):
        body.append(rects(px, by + bh, 2, H - 10 - (by + bh), ROOF))
    body += [
        rects(0, H - 10, w, 10, GROUND), rects(0, H - 10, w, 2, CURB),
        rects(bx + bw, by - 2, 2, bh + 2, mix(BOARD, "#000000", 0.4)), rects(bx + bw + 2, by - 4, 2, bh + 2, mix(BOARD, "#000000", 0.4)),
        rects(bx + 2, by - 2, bw, 2, mix(BOARD_EDGE, "#ffffff", 0.15)), rects(bx + 4, by - 4, bw, 2, mix(BOARD_EDGE, "#ffffff", 0.15)),
        rects(bx, by, bw, bh, BOARD),
        rects(bx, by, bw, 2, BOARD_EDGE), rects(bx, by + bh - 2, bw, 2, BOARD_EDGE),
        rects(bx, by, 2, bh, BOARD_EDGE), rects(bx + bw - 2, by, 2, bh, BOARD_EDGE),
        rects(bx + 2, by + 2, 8, 2, accent), rects(bx + 2, by + 2, 2, 8, accent),
        f'<g opacity=".22">{path(pf.halo_d(name, bx + 16, by + 16, 2, 1), accent)}</g>',
        tpath(name, bx + 16, by + 16, 2, bright),
    ]
    for i, line in enumerate(desc):
        body.append(tpath(line, bx + 16, by + 38 + i * 18, 2, "#aab6ee"))
    my = by + bh - 24
    x = bx + 16
    meta_color = MUTED
    if proj.get("language"):
        body.append(tpath(proj["language"], x, my, 2, meta_color))
        x += pf.width(proj["language"], 2) + 16
    star = f"★ {proj.get('stars', 0)}"
    body.append(tpath(star, x, my, 2, meta_color))
    x += pf.width(star, 2) + 16
    if proj.get("pushed"):
        try:
            when = fmt_date(cfg, parse_date(proj["pushed"]), with_year=False)
            if x + pf.width(when, 2) <= bx + bw - 16:
                body.append(tpath(when, x, my, 2, meta_color))
        except ValueError:
            pass
    alt = tr(cfg, "alt_project").format(name=proj["name"], desc=" ".join(desc))
    return svg_doc(w, H, alt, "".join(body)), H, alt


def footer_slice(cfg, data, w=W):
    h = 60
    today = parse_date(data["updated"])
    text = f"{tr(cfg, 'updated')}: {fmt_date(cfg, today)}"
    body = [rects(0, 0, w, h, PAVE), rects(0, 0, w, 2, CURB), tpath(text, 52, 26, 2, "#7482b3")]
    alt = tr(cfg, "alt_footer").format(date=fmt_date(cfg, today))
    return svg_doc(w, h, alt, "".join(body)), h, alt


# ---------------------------------------------------------------- Hauptprogramm

def main():
    cfg = load_json(CONFIG_PATH)
    data = load_json(DATA_PATH)
    if not cfg or not data or not data.get("days"):
        sys.exit("fehler: Es fehlen Konfiguration oder Daten (zuerst fetch.py ausführen).")
    accent = cfg.get("accent", "#ffd166")
    model = build_model(data)

    os.makedirs(ASSET_DIR, exist_ok=True)
    for f in os.listdir(ASSET_DIR):
        if f.endswith(".svg"):
            os.remove(os.path.join(ASSET_DIR, f))

    rows = []

    def emit(name, result, href=None, w=W):
        content, h, alt = result
        write_if_changed(os.path.join(ASSET_DIR, name), content)
        return {"file": f"assets/console/{name}", "w": w, "h": h, "alt": alt, "href": href}

    rows.append([emit("scene.svg", scene(cfg, model, accent))])

    projects = data.get("projects", [])
    half = W // 2
    for ri in range(0, len(projects), 2):
        pair = projects[ri: ri + 2]
        if len(pair) == 1:
            rows.append([emit(f"project-{ri + 1}.svg", project_slice(cfg, pair[0], W, accent), pair[0]["url"], W)])
        else:
            rows.append([
                emit(f"project-{ri + 1}.svg", project_slice(cfg, pair[0], half, accent), pair[0]["url"], half),
                emit(f"project-{ri + 2}.svg", project_slice(cfg, pair[1], half, accent), pair[1]["url"], half),
            ])

    rows.append([emit("footer.svg", footer_slice(cfg, data))])

    manifest = json.dumps({"width": W, "rows": rows}, ensure_ascii=False, indent=2) + "\n"
    write_if_changed(MANIFEST_PATH, manifest)
    print(f"{sum(len(r) for r in rows)} SVG-Dateien in {ASSET_DIR} geschrieben.")


if __name__ == "__main__":
    main()
