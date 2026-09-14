"""it.pracuj.pl - offers sit in the react-query cache inside __NEXT_DATA__.

Blocks python-requests at the TLS layer, so common.get() falls back to curl.
"""

from __future__ import annotations

from typing import Any, cast
from urllib.parse import quote

from ..common import Offer, get, next_data, polite

NAME = "pracuj.pl"
BASE = "https://it.pracuj.pl/praca"


def _offers_query(data: dict[str, Any]) -> dict[str, Any] | None:
    queries = (
        data.get("props", {}).get("pageProps", {}).get("dehydratedState", {}).get("queries", [])
    )
    for q in queries:
        if q.get("queryKey", [None])[0] == "jobOffers":
            return q.get("state", {}).get("data")
    return None


def fetch(query: str, max_pages: int = 3) -> list[Offer]:
    offers: list[Offer] = []
    for page in range(1, max_pages + 1):
        url = f"{BASE}/{quote(query)};kw"
        if page > 1:
            url += f"?pn={page}"
        try:
            data = next_data(get(url))
            payload: dict[str, Any] | None = _offers_query(data) if data else None
        except Exception as exc:  # noqa: BLE001
            print(f"  [{NAME}] page {page} failed: {exc}")
            break
        if not payload:
            break
        groups: Any = payload.get("groupedOffers") or []
        if not groups:
            break
        for g in groups:
            sub = cast(dict[str, Any], (g.get("offers") or [{}])[0])

            offers.append(
                Offer(
                    source=NAME,
                    title=(g.get("jobTitle") or "").strip(),
                    company=(g.get("companyName") or "").strip(),
                    url=sub.get("offerAbsoluteUri") or g.get("companyProfileAbsoluteUri") or "",
                    query=query,
                    seniority=",".join(g.get("positionLevels") or []),
                    location=sub.get("displayWorkplace") or "",
                    remote=bool(g.get("isRemoteWorkAllowed")),
                    currency="PLN" if g.get("salaryDisplayText") else "",
                    skills=list(g.get("technologies") or []),
                    text=(g.get("jobDescription") or g.get("aboutProjectShortDescription") or "")[
                        :400
                    ],
                )
            )
        polite()
        if len(groups) < 50:
            break
    return offers
