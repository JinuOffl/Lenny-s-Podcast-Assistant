"""
tools/count_tool.py — Word and token counting utilities.
"""
from __future__ import annotations


def count_words(text: str) -> int:
    """Count whitespace-delimited words."""
    return len(text.split()) if text else 0


def count_sentences(text: str) -> int:
    """Rough sentence count."""
    import re
    return len(re.split(r"[.!?]+", text)) if text else 0


def count_bold_phrases(text: str) -> int:
    """Count **bold** phrases — key Ship30for30 formatting check."""
    import re
    return len(re.findall(r"\*\*[^*]+\*\*", text))


def count_guest_citations(text: str, sources: list) -> int:
    """
    Count how many source guests are explicitly named in the response.
    Used to measure citation quality.
    """
    if not sources:
        return 0
    count = 0
    text_lower = text.lower()
    for src in sources:
        guest = src.get("guest", "")
        if guest and guest.lower() in text_lower:
            count += 1
    return count


def essay_stats(text: str, sources: list) -> dict:
    """Return a stats dict for a Ship30for30 essay."""
    return {
        "word_count": count_words(text),
        "sentence_count": count_sentences(text),
        "bold_phrases": count_bold_phrases(text),
        "guest_citations": count_guest_citations(text, sources),
    }
