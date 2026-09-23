"""Authoritative-domain allow-list and reliability filter for Indian legal sources."""
from __future__ import annotations
from urllib.parse import urlparse
import re
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Priority-ordered domain allow-list for Indian law
# Tier 1 = highest authority; Tier 3 = supplementary
# ---------------------------------------------------------------------------
AUTHORITATIVE_DOMAINS: dict[str, int] = {
    # Tier 1 — official court / government portals
    "sci.gov.in": 1,
    "main.sci.gov.in": 1,
    "supremecourt.gov.in": 1,
    "districts.ecourts.gov.in": 1,
    "hcservices.ecourts.gov.in": 1,
    "legislative.gov.in": 1,
    "indiacode.nic.in": 1,
    "egazette.nic.in": 1,
    "egazette.gov.in": 1,
    "mha.gov.in": 1,
    "legalaffairs.gov.in": 1,
    # Tier 2 — established legal portals / bar council
    "indiankanoon.org": 2,
    "casemine.com": 2,
    "manupatra.com": 2,
    "scconline.com": 2,
    "livelaw.in": 2,
    "barandbench.com": 2,
    "latestlaws.com": 2,
    # Tier 3 — supplementary legal commentary
    "legalservicesindia.com": 3,
    "advocatekhoj.com": 3,
    "taxmann.com": 3,
}

# Patterns for non-legal or low-authority content to reject
_REJECT_PATTERNS = [
    re.compile(r"quora\.com"),
    re.compile(r"reddit\.com"),
    re.compile(r"wikipedia\.org"),
    re.compile(r"\.blogspot\.com"),
    re.compile(r"\.wordpress\.com"),
]


@dataclass
class FilteredResult:
    url: str
    title: str
    content: str
    domain: str
    authority_tier: int  # 1 (highest) – 3 (lowest); 99 = unclassified-but-allowed


def score_result(url: str, title: str, content: str) -> FilteredResult | None:
    """Return a FilteredResult if the URL passes the filter, else None.

    Rejects clearly non-legal domains; ranks known authoritative sources.
    Unknown domains pass through as tier 99 (unclassified).
    """
    if not url:
        return None

    # Hard reject list
    for pat in _REJECT_PATTERNS:
        if pat.search(url):
            return None

    domain = urlparse(url).netloc.lstrip("www.")
    tier = AUTHORITATIVE_DOMAINS.get(domain, 99)

    # Must contain some minimal legal signal even for unclassified sources
    if tier == 99:
        legal_signals = ["judgment", "order", "court", "act", "section", "CrPC", "IPC", "CPC", "article", "writ", "petition"]
        text_lower = (title + " " + content).lower()
        if not any(sig.lower() in text_lower for sig in legal_signals):
            return None

    return FilteredResult(url=url, title=title, content=content, domain=domain, authority_tier=tier)


def filter_and_rank(raw_results: list[dict]) -> list[FilteredResult]:
    """Filter and rank a list of Tavily result dicts.

    Each dict is expected to have keys: url, title, content.
    Returns results sorted by authority tier (ascending = more authoritative).
    """
    filtered = []
    for r in raw_results:
        result = score_result(
            url=r.get("url", ""),
            title=r.get("title", ""),
            content=r.get("content", ""),
        )
        if result:
            filtered.append(result)

    return sorted(filtered, key=lambda x: x.authority_tier)
