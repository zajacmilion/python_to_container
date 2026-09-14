"""Turn a pile of offers into the counts that drive the learning path."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from python_to_container.scraper.common import Offer

from .taxonomy import CANON_CATEGORY, from_offer


def dedupe(offers: list[Offer]) -> list[Offer]:
    """Same job posted to several portals counts once.

    czyjesteldorado re-publishes the other portals, so without this the
    aggregator would double-weight everything it mirrors.
    """
    seen: dict[str, Offer] = {}
    for o in sorted(offers, key=lambda x: x.source.startswith("czyjesteldorado")):
        k = o.key()
        if k not in seen and len(k) > 4:
            seen[k] = o
    return list(seen.values())


def analyse(offers: list[Offer], profile: str = "") -> dict[str, Any]:
    tech: Counter[str] = Counter()
    by_cat: defaultdict[str, Counter[str]] = defaultdict(Counter)
    by_seniority: defaultdict[str, Counter[str]] = defaultdict(Counter)
    cooccur: defaultdict[str, Counter[str]] = defaultdict(Counter)
    salary_of: defaultdict[str, list[float]] = defaultdict(list)

    for o in offers:
        techs = from_offer(o)
        sen = _norm_seniority(o.seniority)
        for t in techs:
            tech[t] += 1
            by_cat[CANON_CATEGORY[t]][t] += 1
            by_seniority[sen][t] += 1
            if o.salary_min and o.salary_max and o.currency == "PLN":
                salary_of[t].append((o.salary_min + o.salary_max) / 2)
            for other in techs:
                if other != t:
                    cooccur[t][other] += 1

    n = len(offers) or 1
    return {
        "profile": profile,
        "offers": len(offers),
        "sources": dict(Counter(o.source.split(":")[0] for o in offers)),
        "tech": [
            {
                "name": t,
                "category": CANON_CATEGORY[t],
                "count": c,
                "pct": round(100 * c / n, 1),
                "median_salary": _median(salary_of.get(t, [])),
                "top_with": [x for x, _ in cooccur[t].most_common(5)],
            }
            for t, c in tech.most_common()
        ],
        "by_category": {
            cat: [{"name": t, "count": c} for t, c in cnt.most_common(12)]
            for cat, cnt in sorted(by_cat.items(), key=lambda kv: -sum(kv[1].values()))
        },
        "by_seniority": {s: dict(c.most_common(15)) for s, c in by_seniority.items()},
    }


def _norm_seniority(raw: str) -> str:
    r = (raw or "").lower()
    for key, label in (
        ("trainee", "junior"),
        ("intern", "junior"),
        ("junior", "junior"),
        ("mid", "mid"),
        ("regular", "mid"),
        ("senior", "senior"),
        ("expert", "lead"),
        ("lead", "lead"),
        ("architect", "lead"),
        ("manager", "lead"),
    ):
        if key in r:
            return label
    return "unspecified"


def _median(xs: list[float]) -> int | None:
    if len(xs) < 3:
        return None
    xs = sorted(xs)
    mid = len(xs) // 2
    v = xs[mid] if len(xs) % 2 else (xs[mid - 1] + xs[mid]) / 2
    return int(round(v / 100.0) * 100)
