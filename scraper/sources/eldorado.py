"""czyjesteldorado.pl - cross-portal aggregator (justjoin, NFJ, pracuj, protocol...).

Useful as a breadth source and as the only practical window onto
theprotocol.it, whose own API rejects unauthenticated calls.
"""
from __future__ import annotations

from urllib.parse import quote

from ..common import Offer, flight_payload, get, json_after, polite

NAME = "czyjesteldorado.pl"
BASE = "https://czyjesteldorado.pl"


def fetch(query: str, max_pages: int = 2) -> list[Offer]:
    offers: list[Offer] = []
    for page in range(1, max_pages + 1):
        url = f"{BASE}/search?q={quote(query)}" + (f"&page={page}" if page > 1 else "")
        try:
            raw = flight_payload(get(url))
        except Exception as exc:  # noqa: BLE001
            print(f"  [{NAME}] page {page} failed: {exc}")
            break
        rows = json_after(raw, '"jobs":[{') or json_after(raw, '"items":[{')
        if not rows:
            break
        for r in rows:
            hl = r.get("highlight") or {}
            raw_kws = list(hl.get("keywords") or []) + list(r.get("keywords") or [])
            kws = [k.replace("<mark>", "").replace("</mark>", "")
                   for k in raw_kws if isinstance(k, str)]
            company = r.get("company") or {}
            href = r.get("url") or ""
            offers.append(Offer(
                source=f"{NAME}:{r.get('source', '?')}",
                title=(r.get("title") or "").strip(),
                company=str(company.get("name") or "").strip(),
                url=(BASE + href) if href.startswith("/") else href,
                query=query,
                seniority=str(r.get("seniority") or ""),
                location=",".join(r.get("cities") or []) if isinstance(r.get("cities"), list) else "",
                remote=bool(r.get("isRemote")),
                salary_min=r.get("normalizedSalaryMin"),
                salary_max=r.get("normalizedSalaryMax"),
                currency="PLN" if r.get("hasSalary") else "",
                skills=kws + [t for t in (r.get("technologies") or []) if isinstance(t, str)],
                text=((r.get("description") or {}).get("summary") or "")[:400],
            ))
        polite()
        if len(rows) < 100:
            break
    return offers
