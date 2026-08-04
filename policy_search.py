"""Keyword search over policy clauses (SRS §3.1, P7, FR-3.1, FR-3.3).

Always returns a generous top-k of matching clauses. When the best match is
weak (score 0 — a genuine keyword miss, e.g. a paraphrase like "can I get my
money back" that never says "refund"), also returns the full clause index
so the caller can re-query by clause ID before concluding the policy doesn't
cover the question. A keyword miss must never masquerade as policy silence
(P7) — that's a worse failure than admitting the search was weak.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

from policy_index import Clause, clause_index, get_clauses

# Generic filler words stripped before scoring, so a paraphrase like "can I
# get my money back" reduces to its one content word ("money") instead of
# spuriously matching on "get"/"back"/"my" — this is what makes the
# weak-match fallback actually trigger rather than a coincidental false hit
# (e.g. clause 1.4's "back in stock" sharing the word "back").
_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "to", "of", "in", "on", "at", "for", "and", "or", "but", "if", "do",
    "does", "did", "can", "could", "will", "would", "should", "may",
    "might", "must", "i", "you", "he", "she", "it", "we", "they", "my",
    "your", "his", "her", "its", "our", "their", "me", "him", "us", "them",
    "this", "that", "these", "those", "what", "which", "who", "whom",
    "get", "got", "back", "with", "about", "how", "so", "just", "please",
    "not", "no",
}


def _tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-zA-Z]+", text.lower())
    return [w for w in words if w not in _STOPWORDS and len(w) > 1]


def _score(query_tokens: list[str], clause: Clause) -> int:
    title_tokens = set(_tokenize(clause.title))
    body_counts = Counter(_tokenize(clause.text))
    score = 0
    for token in query_tokens:
        if token in title_tokens:
            score += 3
        score += body_counts.get(token, 0)
    return score


def search_policy(query: str, top_k: int = 5) -> dict[str, Any]:
    """Keyword search over policy clauses (P1, P7, FR-3.1, FR-3.3).

    Returns `{query, results, weak_match, [full_index]}`. `results` is a
    generous top-k of non-zero-scoring clauses, verbatim. `full_index` is
    included only when `weak_match` is True, so the model can re-query a
    specific clause ID instead of falsely concluding the policy is silent.
    """
    query_tokens = _tokenize(query)
    scored = sorted(
        ((clause, _score(query_tokens, clause)) for clause in get_clauses()),
        key=lambda pair: pair[1],
        reverse=True,
    )
    best_score = scored[0][1] if scored else 0
    weak_match = best_score == 0
    results = [clause.to_dict() for clause, score in scored if score > 0][:top_k]

    response: dict[str, Any] = {
        "query": query,
        "results": results,
        "weak_match": weak_match,
    }
    if weak_match:
        response["full_index"] = clause_index()
    return response
