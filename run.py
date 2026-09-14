"""Scrape Polish IT boards for AI-platform roles and summarise the tech demand.

    python run.py            # full run
    python run.py --quick    # 1 page per query, for a smoke test
"""
from __future__ import annotations

import io
import json
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)

from scraper.aggregate import analyse, dedupe            # noqa: E402
from scraper.sources import eldorado, justjoin, nofluff, pracuj  # noqa: E402

SOURCES = [justjoin, nofluff, pracuj, eldorado]

# What the target job actually gets advertised as in PL.
TARGET_QUERIES = [
    "AI Engineer", "LLM", "RAG", "GenAI", "MLOps",
    "Machine Learning Engineer", "AI Platform", "Prompt Engineer",
    "Data Engineer", "Python AI",
]
# Roles reachable from an SDET/embedded background today.
BRIDGE_QUERIES = [
    "Python automation", "QA automation", "SDET", "Test Automation Engineer",
]

OUT = Path("data")


def collect(queries: list[str], pages: int) -> list:
    offers = []
    for q in queries:
        for mod in SOURCES:
            t0 = time.time()
            try:
                got = mod.fetch(q, max_pages=pages)
            except Exception as exc:  # noqa: BLE001
                print(f"  ! {mod.NAME:22} {q!r} -> {type(exc).__name__}: {exc}")
                continue
            offers.extend(got)
            print(f"  {mod.NAME:22} {q!r:32} {len(got):4} offers  ({time.time() - t0:.1f}s)")
    return offers


def main() -> None:
    quick = "--quick" in sys.argv
    pages = 1 if quick else 3
    OUT.mkdir(exist_ok=True)

    result = {}
    for profile, queries in (("target", TARGET_QUERIES), ("bridge", BRIDGE_QUERIES)):
        print(f"\n=== {profile.upper()} ({len(queries)} queries, {pages} page(s)) ===")
        raw = collect(queries, pages)
        clean = dedupe(raw)
        print(f"  -> {len(raw)} raw, {len(clean)} after dedupe")
        (OUT / f"offers_{profile}.json").write_text(
            json.dumps([o.to_dict() for o in clean], ensure_ascii=False, indent=1),
            encoding="utf-8")
        result[profile] = analyse(clean, profile)

    (OUT / "analysis.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")

    for profile, a in result.items():
        print(f"\n--- {profile}: {a['offers']} offers | sources {a['sources']}")
        for t in a["tech"][:18]:
            sal = f"  ~{t['median_salary']:,} PLN".replace(",", " ") if t["median_salary"] else ""
            print(f"   {t['pct']:5.1f}%  {t['name']:28} {t['category']:20}{sal}")


if __name__ == "__main__":
    main()
