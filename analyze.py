"""Second stage: bucket the scraped offers by title and rank the tech demand.

Reads data/offers_*.json (written by run.py), so it can be re-run and
re-tuned without hitting the portals again.
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import Any

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

from python_to_container.scraper.aggregate import analyse, dedupe  # noqa: E402
from python_to_container.scraper.common import Offer  # noqa: E402
from python_to_container.scraper.relevance import split  # noqa: E402

DATA = Path("data")


def load() -> list[Offer]:
    offers: list[Offer] = []
    for f in DATA.glob("offers_*.json"):
        for d in json.loads(f.read_text(encoding="utf-8")):
            offers.append(Offer(**d))
    return offers


def main() -> None:
    raw = load()
    clean = dedupe(raw)
    buckets = split(clean)
    print(f"loaded {len(raw)} offers -> {len(clean)} unique")
    for k, v in buckets.items():
        print(f"  {k:14} {len(v):5}")

    out: dict[str, Any] = {k: analyse(v, k) for k, v in buckets.items() if v}

    # What the AI roles want that the QA roles don't - the actual gap to close.
    ai = {t["name"]: t["pct"] for t in out["ai_core"]["tech"]}
    qa = {t["name"]: t["pct"] for t in out["qa"]["tech"]}
    gap = sorted(((n, p, p - qa.get(n, 0.0)) for n, p in ai.items() if p >= 3),
                 key=lambda x: -x[2])
    out["gap"] = [{"name": n, "ai_pct": p, "delta": round(d, 1)} for n, p, d in gap]
    out["overlap"] = [{"name": n, "ai_pct": ai[n], "qa_pct": qa[n]}
                      for n in ai if n in qa and ai[n] >= 3 and qa[n] >= 5]

    (DATA / "analysis.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n=== AI/ML roles: {out['ai_core']['offers']} offers ===")
    for t in out["ai_core"]["tech"][:25]:
        sal = f"{t['median_salary']:>7,} PLN".replace(",", " ") if t["median_salary"] else "         -"
        print(f"  {t['pct']:5.1f}%  {t['name']:30} {t['category']:20} {sal}")

    print("\n=== Biggest gaps vs your current QA stack ===")
    for g in out["gap"][:15]:
        print(f"  +{g['delta']:5.1f}pp  {g['name']:30} (in {g['ai_pct']}% of AI roles)")

    print("\n=== Already transferable ===")
    for o in sorted(out["overlap"], key=lambda x: -x["ai_pct"])[:12]:
        print(f"  {o['name']:30} AI {o['ai_pct']:5.1f}%  |  QA {o['qa_pct']:5.1f}%")


if __name__ == "__main__":
    main()
