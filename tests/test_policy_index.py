"""Phase 1 tests for the policy clause parser and keyword search (P1, P7)."""

import policy_index
from policy_search import search_policy


def test_all_expected_clause_ids_present():
    ids = {c.id for c in policy_index.get_clauses()}
    for expected in ["1.1", "1.6", "2.1", "2.3", "2.6", "3.1", "3.3", "4.4", "5.2", "6.2"]:
        assert expected in ids
    # Section 7 has no numbered subclauses — it becomes one section-level
    # clause so its bullets stay searchable and citable.
    assert "7" in ids


def test_clause_2_3_is_verbatim_and_multiline():
    clause = policy_index.get_clause("2.3")
    assert clause is not None
    assert clause["title"] == "Non-returnable categories"
    assert "Jewellery" in clause["text"]
    assert "Innerwear and socks" in clause["text"]
    assert "Gift cards" in clause["text"]
    # The clause body shouldn't leak the next clause's heading.
    assert "Final sale" not in clause["text"]


def test_clause_index_has_no_body_text():
    index = policy_index.clause_index()
    assert {"id", "title"} == set(index[0].keys())
    ids = {entry["id"] for entry in index}
    assert "2.3" in ids


def test_get_clause_unknown_id_returns_none():
    assert policy_index.get_clause("99.9") is None


def test_search_policy_jewellery_returns_clause_2_3_verbatim():
    result = search_policy("jewellery")
    assert result["results"], "expected at least one match for 'jewellery'"
    top = result["results"][0]
    assert top["id"] == "2.3"
    assert "Jewellery" in top["text"]
    assert result["weak_match"] is False


def test_search_policy_paraphrase_never_returns_empty():
    # "money back" never appears verbatim in the policy — this is the P7
    # trap: a naive keyword search would come back empty and the model
    # would wrongly conclude refunds aren't covered.
    result = search_policy("can I get my money back")
    got_refund_clauses = any(r["section_id"] == "3" for r in result["results"])
    got_fallback = result.get("weak_match") and "full_index" in result
    assert got_refund_clauses or got_fallback
    # Never an empty result either way.
    assert result["results"] or result.get("full_index")


def test_weak_match_includes_full_index_covering_all_clauses():
    result = search_policy("xyzzyplorb qwiktzorf frobnicate")
    assert result["weak_match"] is True
    assert "full_index" in result
    assert len(result["full_index"]) == len(policy_index.get_clauses())


def test_strong_match_does_not_include_full_index():
    result = search_policy("footwear shoe box")
    assert result["weak_match"] is False
    assert "full_index" not in result
