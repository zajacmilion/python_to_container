"""nofluffjobs.com - documented-ish public search API."""

from __future__ import annotations

from typing import Any, cast

from ..common import Offer, polite, post_json

NAME = "nofluffjobs.com"
API = (
    "https://nofluffjobs.com/api/search/posting"
    "?limit=100&offset={offset}&salaryCurrency=PLN&salaryPeriod=month&region=pl"
)


def _skills(p: dict[str, Any]) -> list[str]:
    technology = p.get("technology")
    out: list[str] = []
    if isinstance(technology, list):
        tech_list = cast(list[dict[str, Any]], technology)
        out = [str(t.get("value", "")) for t in tech_list]
    tiles: dict[str, Any] = p.get("tiles") or {}
    values = cast(list[dict[str, Any]], tiles.get("values") or [])
    for t in values:
        if t.get("value"):
            out.append(str(t["value"]))
    if isinstance(technology, str) and technology:
        out.append(technology)
    return [s for s in out if s]


def fetch(query: str, max_pages: int = 2) -> list[Offer]:
    offers: list[Offer] = []
    for page in range(max_pages):
        try:
            data = post_json(API.format(offset=page * 100), {"rawSearch": query})
        except Exception as exc:  # noqa: BLE001
            print(f"  [{NAME}] page {page + 1} failed: {exc}")
            break
        postings = cast(list[dict[str, Any]], data.get("postings") or [])
        if not postings:
            break
        for p in postings:
            sal: dict[str, Any] = p.get("salary") or {}
            location: dict[str, Any] = p.get("location") or {}
            places = cast(list[dict[str, Any]], location.get("places") or [])
            city = cast(str, next((pl.get("city") for pl in places if pl.get("city")), ""))
            offers.append(
                Offer(
                    source=NAME,
                    title=(p.get("title") or "").strip(),
                    company=(p.get("name") or "").strip(),
                    url=f"https://nofluffjobs.com/pl/job/{p.get('url') or p.get('id', '')}",
                    query=query,
                    seniority=",".join(p.get("seniority") or []),
                    location=city,
                    remote=bool(location.get("fullyRemote")),
                    salary_min=sal.get("from"),
                    salary_max=sal.get("to"),
                    currency=sal.get("currency") or "",
                    skills=_skills(p),
                    text=(p.get("fullyRemote") and "remote " or "") + (p.get("category") or ""),
                )
            )
        polite()
        if len(postings) < 100:
            break
    return offers
