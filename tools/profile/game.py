#!/usr/bin/env python3
"""Straßenspiel in der README: Züge laufen über GitHub Issues.

Jeder Knopf ist ein Link, der ein vorausgefülltes Issue öffnet ("move: forward" usw.). Eine GitHub Action
ruft dieses Skript mit dem Titel auf, es ändert den Spielstand (assets/game/state.json) und baut den
Spielblock in der README neu. Alle Bilder sind vorab gezeichnet, es wird nichts berechnet oder geholt.

    python tools/profile/game.py "move: forward"
"""
import os
import re
import sys
from urllib.parse import quote_plus

from common import CONFIG_PATH, MANIFEST_PATH, ROOT, esc, load_json, write_if_changed

STATE_PATH = os.path.join(ROOT, "assets", "game", "state.json")
MOVES = ("forward", "back", "enter-left", "enter-right", "exit")


def load_state():
    st = load_json(STATE_PATH) or {}
    return {"pos": int(st.get("pos", 0)), "room": st.get("room")}


def save_state(st):
    import json
    write_if_changed(STATE_PATH, json.dumps(st) + "\n")


def apply(st, move, game):
    pos, room = st["pos"], st["room"]
    doors = {int(k): v for k, v in game["door_pos"].items()}
    if room is None:
        if move == "forward" and pos < game["max"]:
            pos += 1
        elif move == "back" and pos > 0:
            pos -= 1
        elif move == "enter-left" and pos in doors:
            room = doors[pos][0]
        elif move == "enter-right" and pos in doors:
            room = doors[pos][1]
    elif move == "exit":
        room = None
    return {"pos": pos, "room": room}


def issue_url(user, move):
    body = 'Just press "Submit new issue". The street updates in a few seconds and this issue closes itself.'
    return f"https://github.com/{user}/{user}/issues/new?title={quote_plus('move: ' + move)}&body={quote_plus(body)}"


def block(cfg, game, st):
    """HTML-Block mit dem aktuellen Bild und den passenden Knöpfen."""
    user = cfg.get("github_user", "")
    pos, room = st["pos"], st["room"]
    if room is None:
        frame, alt = f"game-street-{pos}.svg", game["alt_street"]
        buttons = []
        doors = {int(k): v for k, v in game["door_pos"].items()}
        if pos in doors:
            buttons.append(("left", issue_url(user, "enter-left")))
        if pos > 0:
            buttons.append(("back", issue_url(user, "back")))
        if pos < game["max"]:
            buttons.append(("forward", issue_url(user, "forward")))
        if pos in doors:
            buttons.append(("right", issue_url(user, "enter-right")))
    else:
        frame = f"game-room-{room + 1}.svg"
        proj = game["projects"][room]
        alt = f"Room: {proj['name']}"
        buttons = []
        if proj.get("url"):
            buttons.append(("repo", proj["url"]))
        buttons.append(("exit", issue_url(user, "exit")))
    lines = ['<p align="center">', f'<img src="./assets/console/{frame}" width="100%" align="top" alt="{esc(alt)}">', "</p>"]
    n = len(buttons)
    parts = []
    for key, href in buttons:
        w = f"{min(100 / n, 24):g}%"
        parts.append(f'<a href="{esc(href)}"><img src="./assets/console/btn-{key}.svg" width="{w}" align="top" alt="{key}"></a>')
    lines += ['<p align="center">', "".join(parts), "</p>"]
    return "\n".join(lines)


def main():
    title = (sys.argv[1] if len(sys.argv) > 1 else "").strip()
    m = re.fullmatch(r"move: (forward|back|enter-left|enter-right|exit)", title)
    manifest = load_json(MANIFEST_PATH)
    if not manifest or "game" not in manifest:
        sys.exit("fehler: manifest.json fehlt (zuerst render.py ausführen).")
    if not m:
        print("kein gueltiger Zug, nichts geaendert.")
        return
    old = load_state()
    new = apply(old, m.group(1), manifest["game"])
    save_state(new)
    print(f"{old} -> {new}")
    import readme
    readme.main()


if __name__ == "__main__":
    main()
