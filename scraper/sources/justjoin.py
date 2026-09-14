"""justjoin.it - offers live in the Next.js App Router streaming payload."""
from __future__ import annotations

from urllib.parse import quote

from ..common import Offer, flight_payload, get, json_after, polite

BASE = "https://justjoin.it"
NAME = "justjoin.it"


def _salary(employment_types: list[dict]) -> tuple[float | None, float | None, str]:
    for et in employment_types or []:
        if et.get("currency") == "PLN" and et.get("from") is not None:
            return et.get("from"), et.get("to"), "PLN"
    return None, None, ""


def fetch(query: str, max_pages: int = 3) -> list[Offer]:
    offers: list[Offer] = []
    for page in range(1, max_pages + 1):
        url = f"{BASE}/job-offers/all-locations?keyword={quote(query)}"
        if page > 1:
            url += f"&page={page}"
        try:
            raw = flight_payload(get(url))
        except Exception as exc:  # noqa: BLE001 - one bad page must not kill the run
            print(f"  [{NAME}] page {page} failed: {exc}")
            break
        rows = json_after(raw, '"data":[{"applyUrl"')
        if not rows:
            break
        for r in rows:
            lo, hi, cur = _salary(r.get("employmentTypes", []))
            offers.append(Offer(
                source=NAME,
                title=(r.get("title") or "").strip(),
                company=(r.get("companyName") or "").strip(),
                url=f"{BASE}/job-offer/{r.get('slug', '')}",
                query=query,
                seniority=r.get("experienceLevel") or "",
                location=r.get("city") or "",
                remote=(r.get("workplaceType") == "remote"),
                salary_min=lo, salary_max=hi, currency=cur,
                skills=list(r.get("requiredSkills") or []) + list(r.get("niceToHaveSkills") or []),
                text=(r.get("body") or "")[:400],
            ))
        polite()
        if len(rows) < 100:
            break
    return offers
