"""Gemeinsame Helfer für fetch.py, render.py und readme.py (nur Standardbibliothek)."""
import datetime
import html
import json
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CONFIG_PATH = os.path.join(ROOT, "profile.config.json")
DATA_PATH = os.path.join(ROOT, "tools", "profile", "data", "profile.json")
ASSET_DIR = os.path.join(ROOT, "assets", "console")
MANIFEST_PATH = os.path.join(ASSET_DIR, "manifest.json")


def load_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def save_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def write_if_changed(path, text):
    """Schreibt nur bei Änderung, damit keine sinnlosen Commits entstehen."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        with open(path, encoding="utf-8") as f:
            if f.read() == text:
                return False
    except FileNotFoundError:
        pass
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return True


_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def esc(s):
    return html.escape(_CTRL.sub("", str(s)), quote=True)


def parse_date(s):
    return datetime.date.fromisoformat(s)


STRINGS = {
    "de": {
        "hello": "Hi, ich bin {name}.",
        "sec_config": "Über mich",
        "sec_growth": "Entwicklung",
        "sec_activity": "Aktivität",
        "sec_milestones": "Meilensteine",
        "sec_projects": "Projekte",
        "path_config": "~/ueber-mich",
        "path_growth": "~/entwicklung",
        "path_activity": "~/aktivitaet",
        "path_milestones": "~/meilensteine",
        "path_projects": "~/projekte",
        "hi": "HALLO, ICH BIN",
        "sign_year": "LETZTES JAHR",
        "sign_days": "AKTIVE TAGE",
        "sign_streak": "BESTE SERIE",
        "sign_total": "INSGESAMT",
        "alt_scene": "{intro} Pixel-Nachtstadt: Jedes Gebäude ist eine Woche, jedes beleuchtete Fenster ein aktiver Tag. {year} Beiträge im letzten Jahr, {days} aktive Tage, längste Serie {streak} Tage, {total} insgesamt.",
        "enter": "EINTRETEN",
        "soon": "BALD",
        "hint_walk": "KLICK IN DIE MITTE, UM WEITERZUGEHEN",
        "hint_end": "ENDE DER STRASSE",
        "leave": "ZURUECK ZUR STADT",
        "back_step": "EINEN SCHRITT ZURUECK",
        "back_street": "ZURUECK AUF DIE STRASSE",
        "construction": "IM AUFBAU",
        "open_repo": "> REPO OEFFNEN",
        "exit": "AUSGANG",
        "alt_room": "Raum zum Projekt {name}: {desc}",
        "hint": "KLICK AUF DIE STADT UND GEH HINEIN",
        "hint_back": "KLICK, UM ZURUECK ZUR STADT ZU GEHEN",
        "alt_street": "Straßenansicht bei Nacht: Hochhäuser mit beleuchteten Fenstern, daran vier Leuchtreklamen: {year} Beiträge im letzten Jahr, {days} aktive Tage, längste Serie {streak} Tage, {total} insgesamt.",
        "growth_sub": "letzte 12 Monate · Beiträge pro Woche",
        "legend_bars": "pro Woche",
        "legend_avg": "4-Wochen-Schnitt",
        "legend_trend": "Trend",
        "stat_year": "Beiträge in 12 Monaten",
        "stat_days": "aktive Tage",
        "stat_streak": "längste Serie (Tage)",
        "stat_total": "Beiträge gesamt",
        "activity_sub": "{n} Beiträge an {d} Tagen",
        "rest_note": "",
        "less": "weniger",
        "more": "mehr",
        "footer_note": "",
        "updated": "Stand",
        "no_desc": "Noch keine Beschreibung.",
        "weekdays": ["Mo", "", "Mi", "", "Fr", "", ""],
        "months": ["Jan", "Feb", "Mär", "Apr", "Mai", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dez"],
        "alt_header": "{name}: {tagline}",
        "alt_config": "Über mich: {lines}",
        "alt_growth": "Wachstumskurve: {total} Beiträge in den letzten 12 Monaten, gleitender 4-Wochen-Schnitt und Trend.",
        "alt_stats": "{year} Beiträge in 12 Monaten, {days} aktive Tage, längste Serie {streak} Tage, {total} Beiträge insgesamt.",
        "alt_activity": "Aktivität der letzten 12 Monate: {n} Beiträge an {d} Tagen.",
        "alt_milestones": "Meilensteine: {items}",
        "alt_projects": "Projekte",
        "alt_project": "Projekt {name}: {desc}",
        "alt_contact": "Kontakt: {label}",
        "alt_footer": "Stand {date}.",
        "thousands": ".",
    },
    "en": {
        "hello": "Hi, I'm {name}.",
        "sec_config": "About me",
        "sec_growth": "Progress",
        "sec_activity": "Activity",
        "sec_milestones": "Milestones",
        "sec_projects": "Projects",
        "path_config": "~/about",
        "path_growth": "~/progress",
        "path_activity": "~/activity",
        "path_milestones": "~/milestones",
        "path_projects": "~/projects",
        "hi": "HI, I'M",
        "sign_year": "PAST YEAR",
        "sign_days": "ACTIVE DAYS",
        "sign_streak": "BEST STREAK",
        "sign_total": "ALL TIME",
        "alt_scene": "{intro} Pixel night city: each building is one week, each lit window an active day. {year} contributions in the past year, {days} active days, longest streak {streak} days, {total} in total.",
        "enter": "ENTER",
        "soon": "SOON",
        "hint_walk": "CLICK THE MIDDLE TO WALK ON",
        "hint_end": "END OF THE STREET",
        "leave": "BACK TO THE CITY",
        "back_step": "ONE STEP BACK",
        "back_street": "BACK TO THE STREET",
        "construction": "UNDER CONSTRUCTION",
        "open_repo": "> OPEN REPO",
        "exit": "EXIT",
        "alt_room": "Room for the project {name}: {desc}",
        "hint": "CLICK THE CITY TO STEP INSIDE",
        "hint_back": "CLICK TO GO BACK TO THE CITY",
        "alt_street": "Street view at night: tall buildings with lit windows and four neon signs: {year} contributions in the past year, {days} active days, longest streak {streak} days, {total} in total.",
        "growth_sub": "last 12 months · contributions per week",
        "legend_bars": "per week",
        "legend_avg": "4-week average",
        "legend_trend": "trend",
        "stat_year": "past-year contributions",
        "stat_days": "active days",
        "stat_streak": "longest streak (days)",
        "stat_total": "contributions total",
        "activity_sub": "{n} contributions on {d} days",
        "rest_note": "",
        "less": "less",
        "more": "more",
        "footer_note": "",
        "updated": "last updated",
        "no_desc": "No description yet.",
        "weekdays": ["Mon", "", "Wed", "", "Fri", "", ""],
        "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "alt_header": "{name}: {tagline}",
        "alt_config": "About me: {lines}",
        "alt_growth": "Growth curve: {total} contributions in the last 12 months, 4-week average and trend.",
        "alt_stats": "{year} contributions in 12 months, {days} active days, longest streak {streak} days, {total} contributions in total.",
        "alt_activity": "Activity of the last 12 months: {n} contributions on {d} days.",
        "alt_milestones": "Milestones: {items}",
        "alt_projects": "Projects",
        "alt_project": "Project {name}: {desc}",
        "alt_contact": "Contact: {label}",
        "alt_footer": "As of {date}.",
        "thousands": ",",
    },
}


def tr(cfg, key):
    lang = cfg.get("lang", "de")
    return STRINGS.get(lang, STRINGS["de"])[key]


def fmt_int(cfg, n):
    sep = tr(cfg, "thousands")
    return f"{int(n):,}".replace(",", sep)


def fmt_date(cfg, d, with_day=True, with_year=True):
    months = tr(cfg, "months")
    if cfg.get("lang", "de") == "en":
        out = months[d.month - 1] + (f" {d.day}" if with_day else "")
        return out + (f", {d.year}" if with_year and with_day else f" {d.year}" if with_year else "")
    parts = []
    if with_day:
        parts.append(f"{d.day}.")
    parts.append(months[d.month - 1])
    if with_year:
        parts.append(str(d.year))
    return " ".join(parts)


def fmt_free_date(cfg, s):
    """Akzeptiert YYYY-MM oder YYYY-MM-DD; sonst wird der Text unverändert genutzt."""
    try:
        if len(s) == 7:
            d = datetime.date.fromisoformat(s + "-01")
            return fmt_date(cfg, d, with_day=False)
        return fmt_date(cfg, datetime.date.fromisoformat(s))
    except ValueError:
        return str(s)
