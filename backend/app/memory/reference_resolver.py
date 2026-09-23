"""Rule-based pronoun and reference resolution — used by the Understand node."""
from __future__ import annotations
import re


# Ordinal words → index (0-based)
_ORDINALS = {
    "first": 0, "second": 1, "third": 2, "fourth": 3, "fifth": 4,
    "1st": 0, "2nd": 1, "3rd": 2, "4th": 3, "5th": 4,
}

_PRONOUN_PATTERNS = [
    re.compile(r"\b(it|this|that|those|them|they|these)\b", re.IGNORECASE),
    re.compile(r"\bthe (?:aforementioned|above[- ]?mentioned|said)\b", re.IGNORECASE),
]


def resolve_references(
    query: str,
    recent_messages: list[dict],
    research_entities: list[dict],
) -> str:
    """Attempt rule-based reference resolution.

    Handles:
    - Ordinal references: "the second issue", "the third case"
    - Pronoun references: "those cases", "it", "them" → inject entity names
    - "those judgments" / "those cases" → replace with entity names from session

    Returns the resolved query string (may be identical if no refs found).
    """
    resolved = query

    # --- Ordinal resolution against recent assistant message content ---
    ordinal_match = re.search(
        r"\bthe\s+(" + "|".join(_ORDINALS.keys()) + r")\s+(\w+)\b",
        query,
        re.IGNORECASE,
    )
    if ordinal_match:
        idx = _ORDINALS.get(ordinal_match.group(1).lower(), 0)
        ref_type = ordinal_match.group(2).lower()  # "issue", "case", "point", etc.

        # Look through recent messages for a numbered/bulleted list matching that type
        for msg in reversed(recent_messages):
            if msg.get("role") != "assistant":
                continue
            items = _extract_list_items(msg["content"], ref_type)
            if idx < len(items):
                target = items[idx]
                resolved = resolved.replace(ordinal_match.group(0), f'"{target}"')
                break

    # --- "those cases/judgments/entities" → inject entity names ---
    if re.search(r"\b(those|these|such)\s+(cases|judgments|statutes|issues|entities|authorities)\b", resolved, re.IGNORECASE):
        entity_names = [e["name"] for e in research_entities if e.get("name")]
        if entity_names:
            entity_list = ", ".join(f'"{n}"' for n in entity_names[:5])
            resolved = re.sub(
                r"\b(those|these|such)\s+(cases|judgments|statutes|issues|entities|authorities)\b",
                entity_list,
                resolved,
                flags=re.IGNORECASE,
            )

    return resolved


def _extract_list_items(text: str, ref_type: str) -> list[str]:
    """Extract numbered or bulleted list items from an assistant message."""
    items: list[str] = []

    # Match lines like "1. Issue: ..." or "- Issue A: ..." or "Issue A: ..."
    patterns = [
        re.compile(r"^\s*\d+[.)]\s+(.+)$", re.MULTILINE),
        re.compile(r"^\s*[-*•]\s+(.+)$", re.MULTILINE),
        re.compile(r"^\s*[A-Z][.)]\s+(.+)$", re.MULTILINE),
    ]
    for pat in patterns:
        matches = pat.findall(text)
        if matches:
            items = [m.strip() for m in matches]
            break

    return items
