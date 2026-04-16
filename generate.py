#!/usr/bin/env python3
"""
Morning Edition — Daily Beverage Industry Magazine
Uses Claude with web_search to fetch & curate stories from
Brewbound, Craft Beer & Brewing, and BevNET.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests",
                           "--break-system-packages", "-q"])
    import requests

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"

CATEGORY_COLORS = {
    "BEER":    "#C8A96E",
    "RTD":     "#6EC8B4",
    "CANNABIS":"#7EC87C",
    "SPIRITS": "#C87C6E",
    "SCIENCE": "#6E8EC8",
    "DEALS":   "#C8C86E",
    "DATA":    "#C86E9E",
    "STARTUP": "#FF6B35",
}

LAYOUT_CSS = {
    "hero":       "background:#0A0A0A;color:#F5F0E8;--accent:#C8A96E;",
    "midnight":   "background:#0D1117;color:#E8F4FD;--accent:#4FC3F7;",
    "alert":      "background:#FAFAFA;color:#1A1A1A;--accent:#E53935;",
    "terminal":   "background:#0C1A0C;color:#39FF14;--accent:#39FF14;",
    "academic":   "background:#F5F0E4;color:#2C1810;--accent:#8B2500;",
    "bigstat":    "background:#1A0533;color:#F8F0FF;--accent:#BF5FFF;",
    "dispatch":   "background:#F0EAD6;color:#1C1208;--accent:#B8860B;",
    "blueprint":  "background:#003153;color:#E8F4FD;--accent:#7EC8E3;",
    "broadsheet": "background:#FFFFF0;color:#1A1A1A;--accent:#333333;",
    "ticker":     "background:#FF3300;color:#FFFFFF;--accent:#FFFF00;",
}


# ─── Claude fetch+curate ───────────────────────────────────────────────────────
def fetch_and_curate() -> list:
    today = datetime.now().strftime("%B %d, %Y")

    system = (
        "You are the editor of 'Morning Edition,' a daily intelligence briefing for craft beverage startup founders. "
        "The reader runs a small brewery and sells a digestive supplement brand (PCMKR) oriented around a meat & fruit lifestyle. "
        "He cares about: beer industry moves, cannabis-infused beverages, spirits, RTDs, openings, closings, acquisitions, "
        "distribution, sales data, weird fermentation/ingredients science, and actionable startup intel. "
        "Skip wine entirely. Skip celebrity fluff. Skip politics.\n\n"
        "TASK: Use web_search to find today's top stories from Brewbound, Craft Beer & Brewing Magazine (beerandbrewing.com), "
        "and BevNET. Search at least these queries:\n"
        "1. brewbound.com latest news\n"
        "2. bevnet.com beer RTD cannabis spirits news\n"
        "3. craft beer brewing magazine latest articles\n"
        "4. craft beer industry news today\n"
        "5. RTD ready to drink beverage news today\n\n"
        "After searching, output ONLY a valid JSON array of exactly 10 stories. "
        "No markdown fences, no explanation, just the raw JSON array.\n"
        "Each element must have these exact keys:\n"
        "rank (int 1-10), source (string), title (original headline), url (string), "
        "headline (your punchy 6-word editorial hed), deck (2-sentence editor note on why this matters), "
        "category (one of: BEER|RTD|CANNABIS|SPIRITS|SCIENCE|DEALS|DATA|STARTUP), "
        "flag_for_reader (bool), flag_reason (string, empty if false), "
        "layout (one of: hero|midnight|alert|terminal|academic|bigstat|dispatch|blueprint|broadsheet|ticker). "
        "Use each layout exactly once in that order for ranks 1-10."
    )

    user = f"Today is {today}. Search for the latest beverage industry stories and curate the top 10."

    print("  Calling Claude with web_search tool…")
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable not set.")

    resp = requests.post(
        ANTHROPIC_API_URL,
        headers={"Content-Type": "application/json", "x-api-key": api_key,
                 "anthropic-version": "2023-06-01"},
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 4000,
            "system": system,
            "tools": [{"type": "web_search_20250305", "name": "web_search"}],
            "messages": [{"role": "user", "content": user}],
        },
    )
    resp.raise_for_status()
    data = resp.json()

    # Pull final text block (after tool use)
    text = ""
    for block in data.get("content", []):
        if block.get("type") == "text":
            text = block["text"]

    # Strip markdown fences
    text = re.sub(r"^```json\s*", "", text.strip())
    text = re.sub(r"```\s*$", "", text)
    text = text.strip()

    # Find JSON array
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if m:
        text = m.group(0)

    return json.loads(text)


# ─── HTML helpers ─────────────────────────────────────────────────────────────
def make_flag(story):
    if not story.get("flag_for_reader"):
        return ""
    return (
        '<div class="flag-banner">'
        '<span class="flag-icon">&#x26A1;</span>'
        f'<span class="flag-text">RELEVANT TO YOU &mdash; {story.get("flag_reason","")}</span>'
        '</div>'
    )


def make_meta(story, dark=False):
    cat     = story.get("category", "BEER")
    cat_col = CATEGORY_COLORS.get(cat, "#C8A96E")
    source  = story.get("source", "")
    dc      = " dark" if dark else ""
    cat_fg  = "color:#fff" if dark else "color:#000"
    return (
        f'<div class="meta-row">'
        f'<span class="source-tag{dc}">{source}</span>'
        f'<span class="cat-tag" style="background:{cat_col};{cat_fg}">{cat}</span>'
        f'</div>'
    )


def story_card(story):
    layout  = story.get("layout", "hero")
    css     = LAYOUT_CSS.get(layout, LAYOUT_CSS["hero"])
    rank    = story.get("rank", 1)
    hed     = story.get("headline", story.get("title", ""))
    deck    = story.get("deck", "")
    url     = story.get("url", "#")
    title   = story.get("title", "")
    fg      = make_flag(story)
    dark    = layout in ("alert", "academic", "dispatch", "broadsheet")
    meta    = make_meta(story, dark=dark)
    lc      = "read-link dark" if dark else "read-link"

    if layout == "hero":
        inner = (
            f'<div class="spread-inner hero-layout">'
            f'<div class="hero-num">{rank:02d}</div>'
            f'<div class="content-zone">{meta}'
            f'<h2 class="headline">{hed}</h2><p class="deck">{deck}</p>{fg}'
            f'<a class="{lc}" href="{url}" target="_blank">READ FULL STORY &rarr;</a>'
            f'<p class="orig-title">&ldquo;{title}&rdquo;</p>'
            f'</div></div>'
        )
    elif layout == "midnight":
        inner = (
            f'<div class="spread-inner midnight-layout">'
            f'<div class="rank-pill">&numero; {rank:02d}</div>'
            f'<div class="content-zone">{meta}'
            f'<h2 class="headline">{hed}</h2><p class="deck">{deck}</p>{fg}'
            f'<a class="{lc}" href="{url}" target="_blank">READ FULL STORY &rarr;</a>'
            f'</div><div class="watermark">{rank:02d}</div></div>'
        )
    elif layout == "alert":
        inner = (
            f'<div class="spread-inner alert-layout">'
            f'<div class="alert-stamp">{rank:02d}</div>'
            f'<div class="content-zone">{meta}'
            f'<h2 class="headline">{hed}</h2><p class="deck">{deck}</p>{fg}'
            f'<a class="{lc}" href="{url}" target="_blank">READ FULL STORY &rarr;</a>'
            f'</div></div>'
        )
    elif layout == "terminal":
        src_slug = story.get("source", "").upper().replace(" ", "_")
        cat = story.get("category", "BEER")
        inner = (
            f'<div class="spread-inner terminal-layout">'
            f'<div class="term-header">MORNING_EDITION://STORY_{rank:02d} &gt; {cat} &gt; {src_slug}</div>'
            f'<div class="term-prompt">$ display --headline</div>'
            f'<h2 class="headline">{hed}</h2>'
            f'<div class="term-prompt">$ cat story.deck</div>'
            f'<p class="deck">{deck}</p>{fg}'
            f'<div class="term-prompt">$ open <a class="read-link" href="{url}" '
            f'target="_blank" style="color:#39FF14">{url[:70]}</a></div>'
            f'</div>'
        )
    elif layout == "academic":
        inner = (
            f'<div class="spread-inner academic-layout">'
            f'<div class="dropcap-num">{rank}</div>'
            f'<div class="content-zone">{meta}'
            f'<h2 class="headline">{hed}</h2><p class="deck">{deck}</p>{fg}'
            f'<div class="academic-rule"></div>'
            f'<a class="{lc}" href="{url}" target="_blank">Source: {story.get("source","")} &mdash; Read in full &rarr;</a>'
            f'</div></div>'
        )
    elif layout == "bigstat":
        inner = (
            f'<div class="spread-inner bigstat-layout">'
            f'<div class="stat-num">{rank:02d}</div>'
            f'<div class="content-zone">{meta}'
            f'<h2 class="headline">{hed}</h2><p class="deck">{deck}</p>{fg}'
            f'<a class="{lc}" href="{url}" target="_blank">READ FULL STORY &rarr;</a>'
            f'</div></div>'
        )
    elif layout == "dispatch":
        inner = (
            f'<div class="spread-inner dispatch-layout">'
            f'<div class="dispatch-num">{rank:02d}</div>'
            f'<div class="dispatch-rule"></div>'
            f'<div class="content-zone">{meta}'
            f'<h2 class="headline">{hed}</h2><p class="deck">{deck}</p>{fg}'
            f'<a class="{lc}" href="{url}" target="_blank">READ FULL STORY &rarr;</a>'
            f'</div></div>'
        )
    elif layout == "blueprint":
        inner = (
            f'<div class="spread-inner blueprint-layout">'
            f'<div class="bp-grid-overlay"></div>'
            f'<div class="bp-rank">[{rank:02d}]</div>'
            f'<div class="content-zone">{meta}'
            f'<h2 class="headline">{hed}</h2><p class="deck">{deck}</p>{fg}'
            f'<a class="{lc}" href="{url}" target="_blank">READ FULL STORY &rarr;</a>'
            f'</div></div>'
        )
    elif layout == "broadsheet":
        inner = (
            f'<div class="spread-inner broadsheet-layout">'
            f'<div class="broadsheet-num">{rank:02d}</div>'
            f'<div class="broadsheet-rule"></div>'
            f'<div class="content-zone">{meta}'
            f'<h2 class="headline">{hed}</h2><p class="deck">{deck}</p>{fg}'
            f'<a class="{lc}" href="{url}" target="_blank">READ FULL STORY &rarr;</a>'
            f'</div></div>'
        )
    elif layout == "ticker":
        cat = story.get("category", "BEER")
        src = story.get("source", "").upper()
        tape = (f"MORNING EDITION &#9733; STORY {rank:02d} &#9733; {cat} &#9733; {src} &#9733; ") * 4
        inner = (
            f'<div class="spread-inner ticker-layout">'
            f'<div class="ticker-tape">{tape}</div>'
            f'<div class="content-zone">{meta}'
            f'<h2 class="headline">{hed}</h2><p class="deck">{deck}</p>{fg}'
            f'<a class="{lc}" href="{url}" target="_blank">READ FULL STORY &rarr;</a>'
            f'</div></div>'
        )
    else:
        inner = f'<div class="content-zone"><h2 class="headline">{hed}</h2><p class="deck">{deck}</p></div>'

    return f'<section class="spread" id="story-{rank}" style="{css}">{inner}</section>'


def toc_html(stories):
    items = []
    for s in stories:
        fl = ' <span class="toc-flag">&#x26A1;</span>' if s.get("flag_for_reader") else ""
        items.append(
            f'<a class="toc-item" href="#story-{s["rank"]}">'
            f'<span class="toc-num">{s["rank"]:02d}</span>'
            f'<span class="toc-hed">{s.get("headline","")}{fl}</span>'
            f'</a>'
        )
    return "\n".join(items)


def build_html(stories, date_str):
    display_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%A, %B %d, %Y")
    cards = "\n".join(story_card(s) for s in stories)
    toc   = toc_html(stories)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Morning Edition &mdash; {display_date}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,100..900;1,9..144,100..900&family=Inter:wght@300;400;500;600;700;900&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{--fraunces:'Fraunces',Georgia,serif;--inter:'Inter',system-ui,sans-serif}}
html{{scroll-behavior:smooth}}
body{{font-family:var(--inter);background:#050505;color:#f0f0f0;overflow-x:hidden}}
.masthead{{background:#050505;border-bottom:3px solid #C8A96E;padding:3rem 5vw 2rem;display:flex;align-items:flex-end;justify-content:space-between;flex-wrap:wrap;gap:1rem}}
.masthead-title{{font-family:var(--fraunces);font-size:clamp(3rem,8vw,7rem);font-weight:900;line-height:.9;color:#F5F0E8;letter-spacing:-.03em}}
.masthead-title span{{color:#C8A96E;font-style:italic}}
.masthead-date{{font-size:clamp(.9rem,1.5vw,1.1rem);font-weight:600;color:#C8A96E;text-transform:uppercase;letter-spacing:.15em}}
.masthead-tagline{{font-family:var(--fraunces);font-size:clamp(.85rem,1.3vw,1rem);font-style:italic;color:rgba(245,240,232,.5);margin-top:.3rem}}
.story-count{{font-size:.75rem;color:rgba(200,169,110,.6);margin-top:.5rem;font-weight:500;letter-spacing:.1em;text-transform:uppercase}}
.toc{{background:#0A0A0A;padding:2.5rem 5vw;border-bottom:1px solid #222}}
.toc-label{{font-size:.7rem;font-weight:700;letter-spacing:.3em;text-transform:uppercase;color:#C8A96E;margin-bottom:1.5rem}}
.toc-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:.4rem}}
.toc-item{{display:flex;align-items:baseline;gap:.75rem;padding:.55rem 0;border-bottom:1px solid #1a1a1a;text-decoration:none;transition:color .2s}}
.toc-item:hover{{color:#C8A96E}}
.toc-num{{font-family:var(--fraunces);font-size:1.1rem;font-weight:700;color:#C8A96E;min-width:2rem;font-style:italic}}
.toc-hed{{font-size:.85rem;color:rgba(245,240,232,.7);line-height:1.3}}
.toc-flag{{color:#FF6B35;font-size:.7rem;margin-left:.4rem}}
.spread{{position:relative;min-height:100vh;padding:5vw;display:flex;flex-direction:column;justify-content:center;overflow:hidden}}
.spread-inner{{position:relative;z-index:2;max-width:1100px;margin:0 auto;width:100%}}
.meta-row{{display:flex;align-items:center;gap:.75rem;margin-bottom:1.5rem;flex-wrap:wrap}}
.source-tag{{font-size:.7rem;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:rgba(245,240,232,.5);border:1px solid rgba(245,240,232,.2);padding:.25rem .6rem;border-radius:2px}}
.source-tag.dark{{color:rgba(0,0,0,.5);border-color:rgba(0,0,0,.2)}}
.cat-tag{{font-size:.65rem;font-weight:800;letter-spacing:.15em;text-transform:uppercase;padding:.3rem .7rem;border-radius:2px}}
.headline{{font-family:var(--fraunces);font-size:clamp(2.2rem,5vw,4.5rem);font-weight:800;line-height:1.05;letter-spacing:-.02em;margin-bottom:1.5rem;max-width:900px}}
.deck{{font-size:clamp(1rem,1.8vw,1.25rem);line-height:1.65;max-width:680px;opacity:.8;margin-bottom:2rem}}
.read-link{{display:inline-block;font-size:.75rem;font-weight:700;letter-spacing:.2em;text-transform:uppercase;color:var(--accent);text-decoration:none;border-bottom:2px solid var(--accent);padding-bottom:.2rem;transition:opacity .2s;margin-top:.5rem}}
.read-link:hover{{opacity:.7}}
.read-link.dark{{color:var(--accent)}}
.orig-title{{font-family:var(--fraunces);font-style:italic;font-size:.85rem;opacity:.35;margin-top:1.5rem;max-width:600px}}
.flag-banner{{display:inline-flex;align-items:center;gap:.6rem;background:#FF6B35;color:#fff;padding:.6rem 1.2rem;border-radius:3px;margin-bottom:1.5rem;max-width:90%}}
.flag-icon{{font-size:1rem}}
.flag-text{{font-size:.72rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;line-height:1.3}}
.hero-layout{{display:grid;grid-template-columns:1fr 2fr;gap:4rem;align-items:center}}
.hero-num{{font-family:var(--fraunces);font-size:clamp(8rem,22vw,20rem);font-weight:900;color:rgba(200,169,110,.1);line-height:.85;font-style:italic;user-select:none}}
@media(max-width:700px){{.hero-layout{{grid-template-columns:1fr}}.hero-num{{display:none}}}}
.midnight-layout{{position:relative}}
.rank-pill{{font-family:var(--fraunces);font-size:1rem;font-style:italic;background:rgba(79,195,247,.15);border:1px solid rgba(79,195,247,.3);color:#4FC3F7;display:inline-block;padding:.4rem 1rem;border-radius:50px;margin-bottom:2rem}}
.watermark{{position:absolute;right:-2vw;top:50%;transform:translateY(-50%);font-family:var(--fraunces);font-size:clamp(10rem,25vw,22rem);font-weight:900;color:rgba(79,195,247,.04);user-select:none;pointer-events:none;line-height:1}}
.alert-layout{{display:grid;grid-template-columns:auto 1fr;gap:3rem;align-items:start}}
.alert-stamp{{font-family:var(--fraunces);font-size:clamp(5rem,14vw,12rem);font-weight:900;color:#E53935;line-height:.9;font-style:italic;border:6px solid #E53935;padding:.5rem 1rem;transform:rotate(-3deg);min-width:120px;text-align:center}}
@media(max-width:700px){{.alert-layout{{grid-template-columns:1fr}}.alert-stamp{{font-size:5rem}}}}
.terminal-layout{{font-family:'Courier New',monospace!important}}
.terminal-layout .headline{{font-family:'Courier New',monospace!important;color:#39FF14;font-weight:400;font-size:clamp(1.8rem,4vw,3.5rem)}}
.terminal-layout .deck{{font-family:'Courier New',monospace!important;color:rgba(57,255,20,.7);font-size:1.05rem}}
.term-header{{font-size:.7rem;color:rgba(57,255,20,.5);margin-bottom:2rem;letter-spacing:.05em;word-break:break-all;font-family:'Courier New',monospace}}
.term-prompt{{font-size:.9rem;color:rgba(57,255,20,.6);margin-bottom:.5rem;margin-top:1rem;font-family:'Courier New',monospace}}
.terminal-layout .flag-banner{{background:rgba(57,255,20,.15);border:1px solid #39FF14;color:#39FF14}}
.academic-layout .dropcap-num{{float:left;font-family:var(--fraunces);font-size:clamp(7rem,18vw,16rem);font-weight:900;line-height:.8;color:rgba(139,37,0,.1);margin-right:1rem;margin-top:.1rem;font-style:italic}}
.academic-layout .headline{{font-style:italic}}
.academic-rule{{height:2px;background:#8B2500;max-width:200px;margin:1.5rem 0;clear:both}}
.bigstat-layout{{text-align:center}}
.stat-num{{font-family:var(--fraunces);font-size:clamp(8rem,28vw,24rem);font-weight:900;font-style:italic;color:rgba(191,95,255,.15);line-height:.85;margin-bottom:1rem}}
.bigstat-layout .headline,.bigstat-layout .deck{{margin-left:auto;margin-right:auto;text-align:center}}
.bigstat-layout .meta-row{{justify-content:center}}
.dispatch-num{{font-family:var(--fraunces);font-size:clamp(3rem,8vw,6rem);font-weight:900;color:#B8860B;font-style:italic;margin-bottom:.5rem}}
.dispatch-rule{{height:3px;background:#B8860B;max-width:80px;margin-bottom:2rem}}
.blueprint-layout .bp-grid-overlay{{position:absolute;inset:0;background-image:linear-gradient(rgba(126,200,227,.05) 1px,transparent 1px),linear-gradient(90deg,rgba(126,200,227,.05) 1px,transparent 1px);background-size:40px 40px;pointer-events:none}}
.bp-rank{{font-family:'Courier New',monospace;font-size:clamp(4rem,10vw,8rem);font-weight:400;color:rgba(126,200,227,.2);margin-bottom:1rem}}
.blueprint-layout .headline{{font-family:'Courier New',monospace;font-weight:700;font-style:normal;font-size:clamp(1.8rem,4vw,3.5rem)}}
.broadsheet-num{{font-family:var(--fraunces);font-size:clamp(6rem,16vw,14rem);font-weight:100;color:rgba(0,0,0,.06);line-height:.9;margin-bottom:-2rem}}
.broadsheet-rule{{height:4px;background:#1A1A1A;width:100%;margin-bottom:2rem}}
.broadsheet-layout .headline{{font-size:clamp(2rem,4vw,3.5rem);font-weight:900}}
.ticker-tape{{background:#FFFF00;color:#FF3300;font-size:.8rem;font-weight:900;letter-spacing:.15em;text-transform:uppercase;padding:.6rem 0;white-space:nowrap;overflow:hidden;margin:0 -5vw 3rem;padding-left:5vw}}
.ticker-layout .headline{{color:#FFFF00;font-size:clamp(2.5rem,6vw,5rem)}}
.ticker-layout .deck{{color:rgba(255,255,255,.85)}}
.ticker-layout .flag-banner{{background:#FFFF00;color:#FF3300}}
.magazine-footer{{background:#050505;border-top:3px solid #C8A96E;padding:3rem 5vw;text-align:center;color:rgba(200,169,110,.5)}}
.magazine-footer p{{font-family:var(--fraunces);font-style:italic;font-size:1rem;margin-bottom:.5rem}}
.magazine-footer small{{font-size:.7rem;letter-spacing:.1em;text-transform:uppercase}}
@keyframes fadeUp{{from{{opacity:0;transform:translateY(28px)}}to{{opacity:1;transform:translateY(0)}}}}
.spread{{animation:fadeUp .6s ease-out both}}
.spread:nth-child(1){{animation-delay:.05s}}
.spread:nth-child(2){{animation-delay:.1s}}
.spread:nth-child(3){{animation-delay:.15s}}
</style>
</head>
<body>
<header class="masthead">
  <div>
    <div class="masthead-title">Morning<br><span>Edition</span></div>
  </div>
  <div class="masthead-meta">
    <div class="masthead-date">{display_date}</div>
    <div class="masthead-tagline">Adult Beverage Intelligence for the Builder</div>
    <div class="story-count">10 Curated Stories &middot; Brewbound &middot; Craft Beer &amp; Brewing &middot; BevNET</div>
  </div>
</header>
<nav class="toc">
  <div class="toc-label">Today&rsquo;s Stories</div>
  <div class="toc-grid">{toc}</div>
</nav>
{cards}
<footer class="magazine-footer">
  <p>That&rsquo;s your Morning Edition.</p>
  <small>Curated daily from Brewbound, Craft Beer &amp; Brewing, and BevNET &middot; {display_date}</small>
</footer>
</body>
</html>"""


# ─── Main ──────────────────────────────────────────────────────────────────────
def main():
    date_str = datetime.now().strftime("%Y-%m-%d")
    out_dir  = Path(__file__).parent / "magazines"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"{date_str}.html"

    print(f"\n🍺  Morning Edition — {date_str}")
    print("=" * 50)

    print("\n[1/2] Fetching & curating stories via Claude web search…")
    stories = fetch_and_curate()
    print(f"  → {len(stories)} stories curated")

    print("\n[2/2] Rendering magazine…")
    html = build_html(stories, date_str)
    out_path.write_text(html, encoding="utf-8")

    size_kb = out_path.stat().st_size / 1024
    print(f"\n✅  Saved → {out_path}  ({size_kb:.1f} KB)")

    for s in stories:
        fl = " ⚡" if s.get("flag_for_reader") else ""
        print(f"  {s['rank']:02d}. [{s.get('category','?'):8s}] {s.get('headline','')}{fl}")

    return str(out_path)


if __name__ == "__main__":
    main()
