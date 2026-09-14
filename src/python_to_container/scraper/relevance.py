"""Classify offers by their job title.

Portal keyword search is unreliable - nofluffjobs' rawSearch in particular
returns most of its database when it cannot parse the phrase. The title is
the honest signal, so bucket on that instead of trusting the query.
"""

from __future__ import annotations

import re

from python_to_container.scraper.common import Offer

BUCKETS: dict[str, re.Pattern[str]] = {
    # The destination: building AI systems and the tooling around them.
    "ai_core": re.compile(
        r"\b(ai|a\.i\.|ml|llm|genai|nlp)\b|artificial intelligence|machine learning|"
        r"generative|deep learning|mlops|llmops|data scien|prompt engineer|"
        r"uczenia maszynowego|sztucznej inteligencji",
        re.I,
    ),
    # Adjacent platform/data roles that hire the same stack.
    "data_platform": re.compile(
        r"data engineer|analytics engineer|platform engineer|big data|"
        r"data platform|inżynier danych|devops",
        re.I,
    ),
    # Where the user is now.
    "qa": re.compile(
        r"\b(qa|sdet|test|tester|testing)\b|automation engineer|"
        r"automatyk|testów|testera",
        re.I,
    ),
}

# Titles that merely mention AI as a buzzword but are not engineering roles.
NOISE = re.compile(
    r"\b(sales|account|recruit|hr\b|marketing|copywrit|teacher|trainer|"
    r"lawyer|prawnik|handlow|sprzedaż|manager of|scrum master)\b",
    re.I,
)


def bucket(offer: Offer) -> str | None:
    title = offer.title or ""
    if NOISE.search(title):
        return None
    # QA wins over ai_core for "AI Test Engineer" only if no AI-build signal;
    # checked in priority order below.
    for name in ("ai_core", "data_platform", "qa"):
        if BUCKETS[name].search(title):
            return name
    return None


def split(offers: list[Offer]) -> dict[str, list[Offer]]:
    out: dict[str, list[Offer]] = {"ai_core": [], "data_platform": [], "qa": []}
    for o in offers:
        b = bucket(o)
        if b:
            out[b].append(o)
    return out
