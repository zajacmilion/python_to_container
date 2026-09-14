"""Shared HTTP + data model for the job-board scrapers."""
from __future__ import annotations

import json
import re
import subprocess
import time
from dataclasses import dataclass, field, asdict
from typing import Any

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

HEADERS = {
    "User-Agent": UA,
    "Accept-Language": "pl-PL,pl;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
}

_session = requests.Session()
_session.headers.update(HEADERS)


def get(url: str, *, timeout: int = 30, allow_curl: bool = True, **kw) -> str:
    """GET a URL, falling back to curl when the site blocks python-requests.

    pracuj.pl fingerprints the TLS handshake and 403s requests/urllib3,
    but serves curl happily.
    """
    try:
        r = _session.get(url, timeout=timeout, **kw)
        if r.status_code == 200:
            return r.text
        if not allow_curl:
            r.raise_for_status()
    except requests.RequestException:
        if not allow_curl:
            raise
    return _curl(url, timeout=timeout)


def _curl(url: str, *, timeout: int = 30) -> str:
    cmd = ["curl", "-sL", "--compressed", "--max-time", str(timeout),
           "-H", f"User-Agent: {UA}",
           "-H", "Accept-Language: pl-PL,pl;q=0.9,en;q=0.8",
           url]
    out = subprocess.run(cmd, capture_output=True, timeout=timeout + 15)
    return out.stdout.decode("utf-8", errors="replace")


def post_json(url: str, payload: dict, *, timeout: int = 30) -> Any:
    r = _session.post(url, json=payload, timeout=timeout,
                      headers={"Content-Type": "application/json"})
    r.raise_for_status()
    return r.json()


def next_data(html: str) -> dict | None:
    """Extract the __NEXT_DATA__ blob used by pracuj.pl / theprotocol.it."""
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                  html, re.S)
    return json.loads(m.group(1)) if m else None


def flight_payload(html: str) -> str:
    """Concatenate the Next.js App Router streaming payload.

    justjoin.it and czyjesteldorado.pl ship their offer list this way.
    """
    chunks = re.findall(r'self\.__next_f\.push\(\[1,"(.*?)"\]\)', html, re.S)
    return "".join(chunks).encode().decode("unicode_escape", errors="ignore")


def json_after(raw: str, marker: str) -> list[dict]:
    """Pull the JSON array that follows `marker` inside a flight payload."""
    out: list[dict] = []
    idx = raw.find(marker)
    if idx < 0:
        return out
    start = raw.find("[", idx)
    if start < 0:
        return out
    depth, in_str, esc = 0, False, False
    for i in range(start, len(raw)):
        ch = raw[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "[{":
            depth += 1
        elif ch in "]}":
            depth -= 1
            if depth == 0:
                try:
                    out = json.loads(raw[start:i + 1])
                except json.JSONDecodeError:
                    pass
                break
    return out if isinstance(out, list) else []


@dataclass
class Offer:
    source: str
    title: str
    company: str
    url: str
    query: str = ""
    seniority: str = ""
    location: str = ""
    remote: bool = False
    salary_min: float | None = None
    salary_max: float | None = None
    currency: str = ""
    skills: list[str] = field(default_factory=list)
    text: str = ""

    def key(self) -> str:
        """Identity for cross-portal dedupe."""
        norm = lambda s: re.sub(r"[^a-z0-9]", "", (s or "").lower())
        return f"{norm(self.company)}|{norm(self.title)}"

    def to_dict(self) -> dict:
        return asdict(self)


def polite(seconds: float = 0.7) -> None:
    time.sleep(seconds)
