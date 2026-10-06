#!/usr/bin/env python3
"""Setzt die SVG-Scheiben in README.md ein, aber nur zwischen den Markierungen.

Alles außerhalb von <!-- console:start --> und <!-- console:end --> bleibt von Hand editierbar.
"""
import os
import re
import sys

from common import MANIFEST_PATH, ROOT, esc, load_json, write_if_changed

START = "<!-- console:start -->"
END = "<!-- console:end -->"


def build_block(manifest):
    lines = ['<p align="center">']
    for row in manifest["rows"]:
        n = len(row)
        parts = []
        for item in row:
            width = "100%" if n == 1 else f"{100 / n:g}%"
            img = f'<img src="./{item["file"]}" width="{width}" align="top" alt="{esc(item["alt"])}">'
            if item.get("href"):
                img = f'<a href="{esc(item["href"])}">{img}</a>'
            parts.append(img)
        # Bilder in einer Reihe stehen ohne Leerraum nebeneinander, sonst entstehen Lücken.
        lines.append("".join(parts))
    lines.append("</p>")
    return "\n".join(lines)


def main():
    manifest = load_json(MANIFEST_PATH)
    if not manifest:
        sys.exit("fehler: manifest.json fehlt (zuerst render.py ausführen).")
    path = os.path.join(ROOT, "README.md")
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if text.count(START) != 1 or text.count(END) != 1:
        sys.exit(f"fehler: README.md braucht genau je eine Markierung {START} und {END}.")
    block = f"{START}\n{build_block(manifest)}\n{END}"
    new = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block, text, flags=re.S)
    changed = write_if_changed(path, new)
    print("README.md aktualisiert." if changed else "README.md unverändert.")


if __name__ == "__main__":
    main()
