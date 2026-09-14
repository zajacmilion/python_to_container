"""nofluffjobs.com - documented-ish public search API."""
from __future__ import annotations

from ..common import Offer, polite, post_json

NAME = "nofluffjobs.com"
API = ("https://nofluffjobs.com/api/search/posting"
       "?limit=100&offset={offset}&salaryCurrency=PLN&salaryPeriod=month&region=pl")


def _skills(p: dict) -> list[str]:
    out = [t.get("value", "") for t in (p.get("technology") or [])] if isinstance(p.get("technology"), list) else []
    tiles = p.get("tiles") or {}
    for t in (tiles.get("values") or []):
        if isinstance(t, dict) and t.get("value"):
            out.append(str(t["value"]))
    if p.get("technology") and isinstance(p["technology"], str):
        out.append(p["technology"])
    return [s for s in out if s]


def fetch(query: str, max_pages: int = 2) -> list[Offer]:
    offers: list[Offer] = []
    for page in range(max_pages):
        try:
            data = post_json(API.format(offset=page * 100), {"rawSearch": query})
        except Exception as exc:  # noqa: BLE001
            print(f"  [{NAME}] page {page + 1} failed: {exc}")
            break
        postings = data.get("postings") or []
        if not postings:
            break
        for p in postings:
            sal = p.get("salary") or {}
            places = (p.get("location") or {}).get("places") or []
            city = next((pl.get("city") for pl in places if pl.get("city")), "")
            offers.append(Offer(
                source=NAME,
                title=(p.get("title") or "").strip(),
                company=(p.get("name") or "").strip(),
                url=f"https://nofluffjobs.com/pl/job/{p.get('url') or p.get('id', '')}",
                query=query,
                seniority=",".join(p.get("seniority") or []),
                location=city,
                remote=bool((p.get("location") or {}).get("fullyRemote")),
                salary_min=sal.get("from"), salary_max=sal.get("to"),
                currency=sal.get("currency") or "",
                skills=_skills(p),
                text=(p.get("fullyRemote") and "remote " or "") + (p.get("category") or ""),
            ))
        polite()
        if len(postings) < 100:
            break
    return offers
