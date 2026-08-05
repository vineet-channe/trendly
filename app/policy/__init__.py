"""Policy clause index and keyword search."""

from app.policy.index import clause_index, get_clause, get_clauses
from app.policy.search import search_policy

__all__ = ["clause_index", "get_clause", "get_clauses", "search_policy"]
