"""Single internal legal search interface wrapping Tavily.

The LangGraph retrieve node only calls `legal_search()` — provider details
are hidden here so swapping Tavily never touches agent code.
"""
from __future__ import annotations
from dataclasses import dataclass

from tavily import TavilyClient

from app.core.config import get_settings
from app.core.logging import get_logger
from app.web_search.query_builder import build_search_queries
from app.web_search.source_filter import filter_and_rank, FilteredResult

logger = get_logger(__name__)

_client: TavilyClient | None = None


def _get_client() -> TavilyClient:
    global _client
    if _client is None:
        _client = TavilyClient(api_key=get_settings().tavily_api_key)
    return _client


@dataclass
class WebResult:
    url: str
    title: str
    content: str
    domain: str
    authority_tier: int


async def legal_search(
    resolved_query: str,
    context_entities: list[str] | None = None,
    max_results: int = 6,
) -> list[WebResult]:
    """Run legal-focused web search for the given query.

    1. Build targeted search queries (query_builder).
    2. Search via Tavily with an Indian legal domain include-list.
    3. Filter and rank results (source_filter).

    Returns up to max_results results, sorted by authority tier.
    """
    client = _get_client()
    queries = build_search_queries(resolved_query, context_entities)

    seen_urls: set[str] = set()
    all_raw: list[dict] = []

    primary_query = queries[0] if queries else resolved_query
    try:
        response = client.search(
            query=primary_query,
            search_depth="basic",
            max_results=max_results + 2,
            include_domains=[
                "sci.gov.in", "main.sci.gov.in", "supremecourt.gov.in",
                "districts.ecourts.gov.in", "legislative.gov.in",
                "indiacode.nic.in", "egazette.gov.in", "indiankanoon.org",
                "livelaw.in", "barandbench.com", "casemine.com",
            ],
        )
        for r in response.get("results", []):
            if r.get("url") not in seen_urls:
                seen_urls.add(r.get("url", ""))
                all_raw.append(r)
    except Exception as exc:
        logger.warning("Tavily search failed for query '%s': %s", primary_query[:60], exc)

    filtered = filter_and_rank(all_raw)
    logger.info("Legal search: %d results after filtering for '%s...'", len(filtered), resolved_query[:60])

    return [
        WebResult(
            url=r.url,
            title=r.title,
            content=r.content,
            domain=r.domain,
            authority_tier=r.authority_tier,
        )
        for r in filtered[:max_results]
    ]
