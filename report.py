"""Third stage: turn data/analysis.json into a static HTML summary.

Reads the output of analyze.py, so it can be re-run and re-styled without
touching the portals or re-ranking anything.

    python report.py    # -> data/report.html
"""
from __future__ import annotations

import json
from html import escape
from pathlib import Path

DATA = Path("data")
BUCKET_LABELS = {
    "ai_core": "AI / ML core roles",
    "data_platform": "Data platform roles",
    "qa": "QA / test automation roles",
}


def bar(pct: float) -> str:
    return f'<div class="bar" style="width:{min(pct, 100):.1f}%"></div>'


def tech_table(tech: list[dict], limit: int = 20) -> str:
    rows = []
    for t in tech[:limit]:
        sal = f"{t['median_salary']:,} PLN".replace(",", " ") if t["median_salary"] else "–"
        rows.append(f"""
        <tr>
          <td>{escape(t['name'])}</td>
          <td class="cat">{escape(t['category'])}</td>
          <td class="pct">{t['pct']:.1f}%{bar(t['pct'])}</td>
          <td class="sal">{sal}</td>
        </tr>""")
    return f"""
    <table>
      <thead><tr>
        <th>Technology</th><th>Category</th><th>Share of offers</th><th>Median salary</th>
      </tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>"""


def bucket_section(key: str, data: dict) -> str:
    sources = ", ".join(f"{k} ({v})" for k, v in data["sources"].items())
    return f"""
    <section>
      <h2>{escape(BUCKET_LABELS.get(key, key))}</h2>
      <p class="meta">{data['offers']} offers &middot; {sources}</p>
      {tech_table(data['tech'])}
    </section>"""


def gap_section(gap: list[dict]) -> str:
    rows = []
    for g in gap[:15]:
        rows.append(f"""
        <tr>
          <td>{escape(g['name'])}</td>
          <td class="pct">+{g['delta']:.1f}pp{bar(g['delta'] * 2)}</td>
          <td class="sal">{g['ai_pct']:.1f}% of AI roles</td>
        </tr>""")
    return f"""
    <section>
      <h2>Biggest gaps vs the QA baseline</h2>
      <table>
        <thead><tr><th>Technology</th><th>Gap</th><th>Context</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </section>"""


def load_offers() -> list[dict]:
    offers = []
    for f in sorted(DATA.glob("offers_*.json")):
        profile = f.stem.removeprefix("offers_")
        for o in json.loads(f.read_text(encoding="utf-8")):
            o["profile"] = profile
            offers.append(o)
    return offers


def salary_range(o: dict) -> str:
    lo, hi, cur = o.get("salary_min"), o.get("salary_max"), o.get("currency")
    if not lo and not hi:
        return "–"
    if lo and hi and lo != hi:
        return f"{lo:,.0f}–{hi:,.0f} {cur}".replace(",", " ")
    return f"{(lo or hi):,.0f} {cur}".replace(",", " ")


def offers_section(offers: list[dict]) -> str:
    profiles = sorted({o["profile"] for o in offers})
    sources = sorted({o["source"].split(":")[0] for o in offers})

    rows = []
    for o in offers:
        skills = ", ".join(o.get("skills") or [])
        source = o["source"].split(":")[0]
        text = escape((o["title"] + " " + o["company"] + " " + skills).lower())
        remote = " \U0001f3e0" if o.get("remote") else ""
        title_cell = (f'<a href="{escape(o["url"])}" target="_blank" rel="noopener">'
                      f'{escape(o["title"])}</a>')
        rows.append(f"""
        <tr data-profile="{escape(o['profile'])}" data-source="{escape(source)}" data-text="{text}">
          <td>{title_cell}</td>
          <td>{escape(o['company'])}</td>
          <td class="cat">{escape(o.get('seniority') or '–')}</td>
          <td class="cat">{escape(o.get('location') or '–')}{remote}</td>
          <td class="sal">{escape(salary_range(o))}</td>
          <td class="cat" title="{escape(skills)}">{escape(source)}</td>
        </tr>""")

    profile_opts = "".join(f'<option value="{escape(p)}">{escape(p)}</option>' for p in profiles)
    source_opts = "".join(f'<option value="{escape(s)}">{escape(s)}</option>' for s in sources)

    return f"""
    <section>
      <h2>Offers ({len(offers)})</h2>
      <div class="controls">
        <input id="q" type="search" placeholder="Search title, company, skills…">
        <select id="profile-filter"><option value="">All profiles</option>{profile_opts}</select>
        <select id="source-filter"><option value="">All sources</option>{source_opts}</select>
        <span id="count" class="meta"></span>
      </div>
      <table id="offers">
        <thead><tr><th>Title</th><th>Company</th><th>Seniority</th><th>Location</th><th>Salary</th><th>Source</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </section>
    <script>
      (function() {{
        const q = document.getElementById('q');
        const pf = document.getElementById('profile-filter');
        const sf = document.getElementById('source-filter');
        const count = document.getElementById('count');
        const rows = Array.from(document.querySelectorAll('#offers tbody tr'));
        function apply() {{
          const needle = q.value.trim().toLowerCase();
          const profile = pf.value, source = sf.value;
          let shown = 0;
          for (const r of rows) {{
            const ok = (!needle || r.dataset.text.includes(needle))
              && (!profile || r.dataset.profile === profile)
              && (!source || r.dataset.source === source);
            r.hidden = !ok;
            if (ok) shown++;
          }}
          count.textContent = `${{shown}} / ${{rows.length}} shown`;
        }}
        q.addEventListener('input', apply);
        pf.addEventListener('change', apply);
        sf.addEventListener('change', apply);
        apply();
      }})();
    </script>"""


def overlap_section(overlap: list[dict]) -> str:
    rows = []
    for o in sorted(overlap, key=lambda x: -x["ai_pct"])[:12]:
        rows.append(f"""
        <tr>
          <td>{escape(o['name'])}</td>
          <td class="sal">AI {o['ai_pct']:.1f}%</td>
          <td class="sal">QA {o['qa_pct']:.1f}%</td>
        </tr>""")
    return f"""
    <section>
      <h2>Already transferable</h2>
      <table>
        <thead><tr><th>Technology</th><th>AI roles</th><th>QA roles</th></tr></thead>
        <tbody>{''.join(rows)}</tbody>
      </table>
    </section>"""


STYLE = """
body {
  font: 15px/1.4 system-ui, sans-serif; max-width: 900px; margin: 2rem auto;
  padding: 0 1rem; color: #1a1a1a;
}
h1 { margin-bottom: 0.2rem; }
.meta { color: #666; margin-top: 0; }
section { margin: 2.5rem 0; }
h2 { border-bottom: 2px solid #eee; padding-bottom: 0.3rem; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; padding: 0.4rem 0.6rem; border-bottom: 1px solid #eee; }
th { color: #666; font-weight: 600; font-size: 0.85rem; text-transform: uppercase; }
.cat { color: #666; font-size: 0.9rem; }
.sal { color: #444; white-space: nowrap; }
.pct { position: relative; width: 40%; }
.bar {
  position: absolute; left: 0; bottom: 2px; height: 4px;
  background: #3b6ea5; border-radius: 2px;
}
.controls {
  display: flex; gap: 0.6rem; align-items: center; margin-bottom: 0.6rem; flex-wrap: wrap;
}
.controls input, .controls select { padding: 0.3rem 0.5rem; font: inherit; }
.controls input { flex: 1; min-width: 200px; }
tr[hidden] { display: none; }
"""


def main() -> None:
    analysis = json.loads((DATA / "analysis.json").read_text(encoding="utf-8"))

    body = [bucket_section(k, analysis[k]) for k in BUCKET_LABELS if k in analysis]
    if analysis.get("gap"):
        body.append(gap_section(analysis["gap"]))
    if analysis.get("overlap"):
        body.append(overlap_section(analysis["overlap"]))

    offers = load_offers()
    if offers:
        body.append(offers_section(offers))

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>AI job-market scan (PL)</title>
<style>{STYLE}</style>
</head>
<body>
<h1>AI job-market scan (PL)</h1>
<p class="meta">Generated from data/analysis.json</p>
{''.join(body)}
</body>
</html>"""

    out = DATA / "report.html"
    out.write_text(html, encoding="utf-8")
    print(f"-> {out}")


if __name__ == "__main__":
    main()
