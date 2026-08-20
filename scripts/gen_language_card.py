#!/usr/bin/env python3
"""Render cards/languages-{light,dark}.svg from the GitHub GraphQL API.

Ranking is by *number of repositories where a language is the primary one*, not by
byte count. Byte count is dominated by build output -- creative-lab and
rams-design-system alone hold 46 MB of generated HTML, which would report ~62% HTML
for an account that mostly writes Python.

Uses the workflow's built-in GITHUB_TOKEN; no extra secret to provision.

Two files, not one file with a prefers-color-scheme media query: an SVG loaded via
<img> resolves that query against the OS theme, not GitHub's own light/dark toggle,
so a light-OS user reading GitHub in dark mode would get dark text on dark. A
<picture> with two sources follows the GitHub theme correctly.

Geometry (440x200, rx=12, hairline stroke, ~22px padding) deliberately mirrors the
ghfind card it sits beside, so the pair renders at identical size and aligns on both
the top and the bottom edge.
"""
import json, os, subprocess
from collections import Counter

USER = os.environ.get("CARD_USER", "Jah-yee")
OUTDIR = os.environ.get("CARD_OUTDIR", "cards")
W, H, PAD = 440, 200, 22
ACCENT = "#FA5C21"

THEMES = {
    "light": dict(bg="#ffffff", stroke=ACCENT, fg="#1f2328", muted="#656d76", rail="#d8dee4"),
    "dark":  dict(bg="#0a0a0b", stroke=ACCENT, fg="#f4f4f5", muted="#a1a1aa", rail="#2a2a2e"),
}

QUERY = """
query($login:String!, $cursor:String){
  user(login:$login){
    repositories(first:100, after:$cursor, ownerAffiliations:OWNER,
                 isFork:false, privacy:PUBLIC){
      pageInfo{ hasNextPage endCursor }
      nodes{ isArchived primaryLanguage{ name color } }
    }
  }
}
"""


def fetch():
    counts, colors, cursor = Counter(), {}, None
    for _ in range(20):  # hard stop at 2000 repos
        args = ["gh", "api", "graphql", "-f", f"query={QUERY}", "-F", f"login={USER}"]
        if cursor:
            args += ["-F", f"cursor={cursor}"]
        out = subprocess.run(args, capture_output=True, text=True, check=True).stdout
        repos = json.loads(out)["data"]["user"]["repositories"]
        for r in repos["nodes"]:
            lang = r.get("primaryLanguage")
            if lang and not r["isArchived"]:
                counts[lang["name"]] += 1
                colors[lang["name"]] = lang["color"] or "#8b949e"
        if not repos["pageInfo"]["hasNextPage"]:
            break
        cursor = repos["pageInfo"]["endCursor"]
    return counts, colors


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build(counts, colors, theme):
    t = THEMES[theme]
    total = sum(counts.values())
    if not total:
        raise SystemExit("no language data returned; refusing to write an empty card")

    top = counts.most_common(6)
    rest = total - sum(n for _, n in top)
    segs = [(n_, c_, colors[n_]) for n_, c_ in top]
    if rest > 0:
        segs.append(("Other", rest, t["rail"]))

    inner = W - PAD * 2
    gap = 2
    span = inner - gap * (len(segs) - 1)

    bar_y, bar_h, x = 64, 9, float(PAD)
    bars = []
    for name, n, color in segs:
        w = max(span * n / total, 2.0)
        bars.append(
            f'  <rect x="{x:.2f}" y="{bar_y}" width="{w:.2f}" height="{bar_h}" '
            f'rx="{bar_h/2:.1f}" fill="{color}"><title>{esc(name)}: {n} repos</title></rect>'
        )
        x += w + gap

    col_w = inner / 2
    col_x = [PAD, PAD + col_w + 6]
    rows_y = [104, 138, 172]
    legend = []
    for i, (name, n, color) in enumerate(segs[:6]):
        cx, cy = col_x[i % 2], rows_y[i // 2]
        right = cx + col_w - 12
        legend.append(
            f'  <g><rect x="{cx}" y="{cy-9}" width="3" height="12" rx="1.5" fill="{color}"/>'
            f'<text class="n" x="{cx+11}" y="{cy}">{esc(name)}</text>'
            f'<text class="p" x="{right:.0f}" y="{cy}" text-anchor="end">{n/total*100:.0f}%</text>'
            f'<text class="c" x="{cx+11}" y="{cy+13}">{n} repo{"" if n == 1 else "s"}</text></g>'
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Top languages by number of repositories">
<title>Top languages across {total} public repositories</title>
<style>
  text {{ font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas, monospace; }}
  .h {{ font-size: 11.5px; font-weight: 700; letter-spacing: 1.6px; fill: {ACCENT}; }}
  .s {{ font-size: 9.5px; letter-spacing: .2px; fill: {t["muted"]}; }}
  .n {{ font-size: 12px; font-weight: 600; fill: {t["fg"]}; }}
  .p {{ font-size: 12px; font-weight: 600; fill: {t["fg"]}; font-variant-numeric: tabular-nums; }}
  .c {{ font-size: 9px; letter-spacing: .2px; fill: {t["muted"]}; }}
</style>
  <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="12" fill="{t["bg"]}" stroke="{t["stroke"]}" stroke-opacity="0.32"/>
  <text class="h" x="{PAD}" y="34">/// LANGUAGES</text>
  <text class="s" x="{PAD}" y="50">ranked by primary language · {total} public repos</text>
{chr(10).join(bars)}
{chr(10).join(legend)}
</svg>
'''


if __name__ == "__main__":
    c, col = fetch()
    os.makedirs(OUTDIR, exist_ok=True)
    for theme in THEMES:
        p = os.path.join(OUTDIR, f"languages-{theme}.svg")
        with open(p, "w") as f:
            f.write(build(c, col, theme))
        print(f"wrote {p}")
    print(f"{sum(c.values())} repos, {len(c)} languages")
