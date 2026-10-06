#!/usr/bin/env python3
"""Holt Contribution-Daten und Repos von GitHub (GraphQL) und speichert sie als JSON.

Nur Standardbibliothek. Schlägt der Abruf fehl, bleiben die Werte vom Vortag stehen.
`--demo` erzeugt Beispieldaten ohne Netzwerk, um das Design lokal zu testen.
"""
import argparse
import datetime
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request

from common import CONFIG_PATH, DATA_PATH, load_json, save_json

API = "https://api.github.com/graphql"

PROFILE_QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection { contributionYears }
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100,
                 orderBy: {field: PUSHED_AT, direction: DESC}) {
      totalCount
      nodes {
        name description url stargazerCount pushedAt isArchived
        primaryLanguage { name color }
      }
    }
  }
}
"""


def warn(msg):
    print(f"warnung: {msg}", file=sys.stderr)


def graphql(token, query, variables=None, tries=3):
    body = json.dumps({"query": query, "variables": variables or {}}).encode()
    req = urllib.request.Request(
        API,
        data=body,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "profile-updater",
        },
    )
    last = None
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                res = json.load(r)
        except urllib.error.HTTPError as ex:
            if ex.code in (401, 403, 404):
                raise RuntimeError(f"GitHub antwortet mit {ex.code} (Token oder Name prüfen)")
            last = ex
            time.sleep(2 * (attempt + 1))
            continue
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as ex:
            last = ex
            time.sleep(2 * (attempt + 1))
            continue
        if res.get("errors"):
            raise RuntimeError("GraphQL: " + "; ".join(e.get("message", "?") for e in res["errors"]))
        return res["data"]
    raise RuntimeError(f"GitHub nicht erreichbar: {last}")


def years_query(years):
    # contributionsCollection deckt höchstens ein Jahr pro Feld ab, daher ein Alias pro Jahr.
    parts = []
    for y in years:
        parts.append(
            f'y{y}: contributionsCollection(from: "{y}-01-01T00:00:00Z", to: "{y}-12-31T23:59:59Z") {{'
            " contributionCalendar { weeks { contributionDays { date contributionCount } } } }"
        )
    return "query($login: String!) { user(login: $login) { " + " ".join(parts) + " } }"


def pick_projects(nodes, cfg, login):
    pcfg = cfg.get("projects", {})
    count = int(pcfg.get("count", 4))
    exclude = {x.lower() for x in pcfg.get("exclude", [])} | {login.lower()}
    by_name = {n["name"].lower(): n for n in nodes}

    def to_project(n, desc=None):
        lang = n.get("primaryLanguage") or {}
        return {
            "name": n["name"],
            "description": desc if desc else (n.get("description") or ""),
            "url": n["url"],
            "stars": n.get("stargazerCount", 0),
            "language": lang.get("name"),
            "language_color": lang.get("color"),
            "pushed": (n.get("pushedAt") or "")[:10],
        }

    chosen = []
    for entry in pcfg.get("pinned", []):
        if isinstance(entry, dict) and entry.get("coming_soon"):
            chosen.append({"name": entry.get("name", "Coming soon"), "description": entry.get("description", ""),
                           "url": None, "stars": 0, "language": None, "language_color": None,
                           "pushed": "", "coming_soon": True})
            continue
        name, desc = (entry, None) if isinstance(entry, str) else (entry["repo"], entry.get("description"))
        name = name.split("/")[-1]
        node = by_name.get(name.lower())
        if node is None:
            warn(f"gepinntes Repo '{name}' nicht gefunden oder nicht öffentlich")
            continue
        chosen.append(to_project(node, desc))
    taken = {p["name"].lower() for p in chosen}
    for n in nodes:
        if len(chosen) >= count:
            break
        if n["isArchived"] or n["name"].lower() in exclude or n["name"].lower() in taken:
            continue
        chosen.append(to_project(n))
    return chosen[:count]


def fetch_github(token, login, cfg, today):
    base = graphql(token, PROFILE_QUERY, {"login": login})["user"]
    if base is None:
        raise RuntimeError(f"Benutzer '{login}' nicht gefunden")
    years = base["contributionsCollection"]["contributionYears"]
    days = {}
    # Alle Jahre in einer Abfrage; bei sehr vielen Jahren in Häppchen.
    for i in range(0, len(years), 6):
        chunk = years[i : i + 6]
        data = graphql(token, years_query(chunk), {"login": login})["user"]
        for y in chunk:
            for week in data[f"y{y}"]["contributionCalendar"]["weeks"]:
                for d in week["contributionDays"]:
                    if d["date"] <= today.isoformat():
                        days[d["date"]] = d["contributionCount"]
    repos = base["repositories"]
    return {
        "days": days,
        "repo_count": repos["totalCount"],
        "projects": pick_projects(repos["nodes"], cfg, login),
    }


def demo_data(today, lang="de"):
    """Deterministische Beispieldaten: Wochentage aktiver, Ruhewochen, langsames Wachstum."""
    rng = random.Random(7)
    start = today - datetime.timedelta(days=900)
    days = {}
    rest_week = set()
    d = start
    total_days = (today - start).days
    while d <= today:
        week_id = (d - start).days // 7
        if week_id not in rest_week and rng.random() < 0.10:
            rest_week.add(week_id)
        progress = (d - start).days / total_days
        base_p = 0.28 + 0.38 * progress
        p = base_p * (1.25 if d.weekday() < 5 else 0.7)
        if week_id in rest_week:
            p *= 0.1
        count = 0
        if rng.random() < p:
            count = 1 + int(rng.expovariate(1 / (1.2 + 3.5 * progress)))
        if count:
            days[d.isoformat()] = count
        d += datetime.timedelta(days=1)
    texts = {
        "de": [
            "Platzhalter: Hier steht später die Beschreibung deines Repos aus GitHub.",
            "Platzhalter: Kurz und konkret, was das Projekt kann und warum es existiert.",
            "Platzhalter: Auch kleine Experimente gehören hierher.",
            "Platzhalter: Maximal zwei Zeilen werden angezeigt, der Rest wird gekürzt.",
        ],
        "en": [
            "Placeholder: the description of your repo from GitHub shows up here.",
            "Placeholder: what the project does and why it exists, short and concrete.",
            "Placeholder: small experiments belong here too.",
            "Placeholder: two lines at most are shown, the rest gets cut off.",
        ],
    }[lang if lang in ("de", "en") else "de"]
    prefix = "beispiel-projekt" if lang == "de" else "example-project"
    meta = [
        (12, "Python", "#3572A5", 3),
        (4, "TypeScript", "#3178c6", 17),
        (0, "Jupyter Notebook", "#DA5B0B", 41),
        (2, "Rust", "#dea584", 66),
    ]
    projects = [
        {
            "name": f"{prefix}-{i}",
            "description": texts[i - 1],
            "url": "https://github.com/DEIN-GITHUB-NAME",
            "stars": stars,
            "language": language,
            "language_color": color,
            "pushed": (today - datetime.timedelta(days=gap)).isoformat(),
        }
        for i, (stars, language, color, gap) in enumerate(meta, start=1)
    ]
    return {"days": days, "repo_count": 14, "projects": projects, "demo": True}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="Beispieldaten statt GitHub-Abruf")
    args = ap.parse_args()

    cfg = load_json(CONFIG_PATH, {})
    data = load_json(DATA_PATH, {})
    today = datetime.datetime.now(datetime.timezone.utc).date()

    if args.demo:
        data = demo_data(today, cfg.get("lang", "de"))
        data["updated"] = today.isoformat()
        save_json(DATA_PATH, data)
        print(f"Demo-Daten für {today} gespeichert.")
        return

    login = cfg.get("github_user", "")
    if not login or login == "DEIN-GITHUB-NAME":
        sys.exit("fehler: In profile.config.json fehlt noch dein github_user.")

    token = os.environ.get("PROFILE_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("fehler: Weder PROFILE_TOKEN noch GITHUB_TOKEN ist gesetzt.")

    try:
        fresh = fetch_github(token, login, cfg, today)
        data.update(fresh)
        data["demo"] = False
        data["updated"] = today.isoformat()
    except Exception as ex:  # bewusst breit: lieber alte Daten als ein leeres Profil
        warn(f"Abruf fehlgeschlagen, alte Daten bleiben: {ex}")
        if not data.get("days") or data.get("demo"):
            # Demo-Daten dürfen nie als "alte Daten" auf einem echten Profil stehen bleiben.
            sys.exit("fehler: Es gibt keine echten alten Daten, auf die ich zurückfallen kann.")
    save_json(DATA_PATH, data)
    print(f"Daten für {login} gespeichert ({len(data['days'])} Tage).")


if __name__ == "__main__":
    main()
