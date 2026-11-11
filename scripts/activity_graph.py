#!/usr/bin/env python3
"""Generate a self-contained contribution activity SVG (no external services)."""
import datetime as dt
import json
import os
import sys
import urllib.request

USER = os.environ.get("GH_USER", "Hamoex")
TOKEN = os.environ["GITHUB_TOKEN"]
OUT = sys.argv[1] if len(sys.argv) > 1 else "activity-graph.svg"
DAYS = 31

BG, FG, ACCENT, GRID, MUTED = "#0d1117", "#ffffff", "#00ff9f", "#1f2a24", "#8b949e"

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch_counts():
    today = dt.datetime.now(dt.timezone.utc).date()
    start = today - dt.timedelta(days=DAYS - 1)
    body = json.dumps({
        "query": QUERY,
        "variables": {
            "login": USER,
            "from": f"{start.isoformat()}T00:00:00Z",
            "to": f"{today.isoformat()}T23:59:59Z",
        },
    }).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if "errors" in data:
        raise SystemExit(f"GraphQL error: {data['errors']}")
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    counts = {d["date"]: d["contributionCount"] for w in weeks for d in w["contributionDays"]}
    days = [start + dt.timedelta(days=i) for i in range(DAYS)]
    return [(d, counts.get(d.isoformat(), 0)) for d in days]


def build_svg(series):
    w, h = 900, 320
    ml, mr, mt, mb = 50, 30, 60, 50
    pw, ph = w - ml - mr, h - mt - mb
    peak = max(c for _, c in series)
    ymax = max(5, peak + (-peak % 5 or 0))
    n = len(series)

    def x(i):
        return ml + pw * i / (n - 1)

    def y(v):
        return mt + ph - ph * v / ymax

    pts = [(x(i), y(c)) for i, (_, c) in enumerate(series)]
    line = " ".join(f"{px:.1f},{py:.1f}" for px, py in pts)
    area = f"{ml},{mt + ph} {line} {ml + pw},{mt + ph}"

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="Contribution activity">',
        '<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{ACCENT}" stop-opacity="0.35"/>'
        f'<stop offset="100%" stop-color="{ACCENT}" stop-opacity="0"/></linearGradient></defs>',
        f'<rect width="{w}" height="{h}" rx="8" fill="{BG}"/>',
        f'<text x="{w / 2}" y="34" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="20" font-weight="600" fill="{ACCENT}">Contribution Activity</text>',
    ]

    step = ymax // 5
    for t in range(0, ymax + 1, step):
        gy = y(t)
        parts.append(f'<line x1="{ml}" y1="{gy:.1f}" x2="{ml + pw}" y2="{gy:.1f}" stroke="{GRID}"/>')
        parts.append(
            f'<text x="{ml - 10}" y="{gy + 4:.1f}" text-anchor="end" font-family="Segoe UI, Arial, sans-serif" font-size="11" fill="{MUTED}">{t}</text>'
        )

    for i, (d, _) in enumerate(series):
        if i % 5 == 0 or i == n - 1:
            parts.append(
                f'<text x="{x(i):.1f}" y="{mt + ph + 22}" text-anchor="middle" font-family="Segoe UI, Arial, sans-serif" font-size="11" fill="{MUTED}">{d.day} {d.strftime("%b")}</text>'
            )

    parts.append(f'<polygon points="{area}" fill="url(#g)"/>')
    parts.append(f'<polyline points="{line}" fill="none" stroke="{ACCENT}" stroke-width="2.5" stroke-linejoin="round"/>')
    for (px, py), (d, c) in zip(pts, series):
        parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.5" fill="{FG}" stroke="{ACCENT}" stroke-width="1.5"><title>{d.isoformat()}: {c}</title></circle>')

    parts.append("</svg>")
    return "\n".join(parts)


if __name__ == "__main__":
    svg = build_svg(fetch_counts())
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Wrote {OUT}")
