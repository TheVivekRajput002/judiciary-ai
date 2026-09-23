"""Reformulates a legal query into targeted search queries for Indian law sources."""
from __future__ import annotations
import re

# Common Indian legal reference patterns to detect and preserve
_SECTION_REF = re.compile(r"[Ss]ection\s+\d+[A-Za-z]?(?:\s+(?:of\s+)?(?:CrPC|CPC|IPC|IEA|Constitution))?")
_ARTICLE_REF = re.compile(r"[Aa]rticle\s+\d+[A-Za-z]?")
_CASE_CITATION = re.compile(r"\(\d{4}\)\s+\d+\s+SCC\s+\d+")


def build_search_queries(
    resolved_query: str,
    context_entities: list[str] | None = None,
    max_queries: int = 3,
) -> list[str]:
    """Generate 1–3 targeted legal search queries from a resolved user query.

    For follow-up queries that reference prior entities, those entities are
    injected as explicit search terms rather than running a generic query.

    Args:
        resolved_query: The query after reference resolution by the understand node.
        context_entities: Names of entities already identified in this session
                          (cases, statutes, issues) — used to seed follow-up searches.
        max_queries: Maximum number of search queries to generate.

    Returns:
        List of search query strings, most specific first.
    """
    queries: list[str] = []

    # Primary: exact resolved query + "India" or "Supreme Court" qualifier if not present
    primary = resolved_query.strip()
    if "India" not in primary and "Indian" not in primary and "Supreme Court" not in primary:
        primary = primary + " India Supreme Court"
    queries.append(primary)

    # Secondary: if context entities exist, build entity-specific query
    if context_entities:
        entity_terms = " ".join(f'"{e}"' for e in context_entities[:3])
        queries.append(f"{entity_terms} India judgment")

    # Tertiary: strip question words and add "judgment" / "case law"
    simplified = re.sub(r"^(what|who|when|where|how|find|explain|tell me|analyze)\b\s*", "", primary, flags=re.IGNORECASE).strip()
    simplified = f"Indian case law {simplified}"
    if simplified not in queries:
        queries.append(simplified)

    return queries[:max_queries]
