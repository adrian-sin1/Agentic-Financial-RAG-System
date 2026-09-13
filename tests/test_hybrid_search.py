from unittest.mock import patch

from src.retrieval.hybrid_search import GROUNDEDNESS_THRESHOLD, hybrid_search


def _chunk(chunk_id, **extra):
    base = {
        "chunk_id": chunk_id,
        "company": "Apple",
        "year": 2025,
        "document_type": "10-K",
        "section": "Item 1A. Risk Factors",
        "page": None,
        "chunk_text": f"text for {chunk_id}",
    }
    base.update(extra)
    return base


def test_returns_empty_when_vector_search_finds_nothing():
    with patch("src.retrieval.hybrid_search.vector_search", return_value=[]):
        results = hybrid_search("irrelevant question")
    assert results == []


def test_groundedness_threshold_rejects_weak_matches():
    weak_matches = [_chunk("doc::sec::0", score=GROUNDEDNESS_THRESHOLD - 0.01)]
    with patch("src.retrieval.hybrid_search.vector_search", return_value=weak_matches):
        results = hybrid_search("capital of Mongolia")
    assert results == []


def test_proceeds_when_best_score_meets_threshold():
    strong_match = [_chunk("doc::sec::0", score=GROUNDEDNESS_THRESHOLD)]
    with (
        patch("src.retrieval.hybrid_search.vector_search", return_value=strong_match),
        patch("src.retrieval.hybrid_search.keyword_search", return_value=[]),
        patch("src.retrieval.hybrid_search.fetch_chunks", return_value={}),
    ):
        results = hybrid_search("a real question", expand_neighbors=False)
    assert len(results) == 1
    assert results[0]["chunk_id"] == "doc::sec::0"


def test_rrf_ranks_chunks_appearing_in_both_lists_above_single_list_matches():
    # "doc::sec::0" is rank 0 in both lists -> should outrank "doc::sec::1",
    # which is rank 0 in vector only
    vector_results = [_chunk("doc::sec::0", score=0.9), _chunk("doc::sec::1", score=0.8)]
    keyword_results = [_chunk("doc::sec::0", match_count=5)]

    with (
        patch("src.retrieval.hybrid_search.vector_search", return_value=vector_results),
        patch("src.retrieval.hybrid_search.keyword_search", return_value=keyword_results),
        patch("src.retrieval.hybrid_search.fetch_chunks", return_value={}),
    ):
        results = hybrid_search("question", expand_neighbors=False)

    assert [r["chunk_id"] for r in results] == ["doc::sec::0", "doc::sec::1"]
    assert results[0]["rrf_score"] > results[1]["rrf_score"]


def test_top_k_limits_the_number_of_ranked_results():
    vector_results = [_chunk(f"doc::sec::{i}", score=0.9 - i * 0.01) for i in range(10)]
    with (
        patch("src.retrieval.hybrid_search.vector_search", return_value=vector_results),
        patch("src.retrieval.hybrid_search.keyword_search", return_value=[]),
        patch("src.retrieval.hybrid_search.fetch_chunks", return_value={}),
    ):
        results = hybrid_search("question", top_k=3, expand_neighbors=False)
    assert len(results) == 3


def test_neighbor_expansion_adds_marked_chunks_without_rrf_score():
    vector_results = [_chunk("doc::sec::5", score=0.9)]
    neighbor_data = {
        "doc::sec::4": _chunk("doc::sec::4"),
        "doc::sec::6": _chunk("doc::sec::6"),
    }
    with (
        patch("src.retrieval.hybrid_search.vector_search", return_value=vector_results),
        patch("src.retrieval.hybrid_search.keyword_search", return_value=[]),
        patch("src.retrieval.hybrid_search.fetch_chunks", return_value=neighbor_data) as mock_fetch,
    ):
        results = hybrid_search("question", expand_neighbors=True)

    mock_fetch.assert_called_once()
    requested_ids = set(mock_fetch.call_args[0][0])
    assert requested_ids == {"doc::sec::4", "doc::sec::6"}

    neighbors = [r for r in results if r["is_neighbor"]]
    assert {r["chunk_id"] for r in neighbors} == {"doc::sec::4", "doc::sec::6"}
    assert all(r["rrf_score"] is None for r in neighbors)


def test_expand_neighbors_false_skips_neighbor_lookup_entirely():
    vector_results = [_chunk("doc::sec::5", score=0.9)]
    with (
        patch("src.retrieval.hybrid_search.vector_search", return_value=vector_results),
        patch("src.retrieval.hybrid_search.keyword_search", return_value=[]),
        patch("src.retrieval.hybrid_search.fetch_chunks") as mock_fetch,
    ):
        results = hybrid_search("question", expand_neighbors=False)

    mock_fetch.assert_not_called()
    assert len(results) == 1


def test_a_ranked_chunks_own_neighbor_is_not_fetched_twice():
    # doc::sec::0 and doc::sec::1 are adjacent and both independently ranked --
    # neither should be re-requested as a "neighbor" of the other
    vector_results = [_chunk("doc::sec::0", score=0.9), _chunk("doc::sec::1", score=0.85)]
    with (
        patch("src.retrieval.hybrid_search.vector_search", return_value=vector_results),
        patch("src.retrieval.hybrid_search.keyword_search", return_value=[]),
        patch("src.retrieval.hybrid_search.fetch_chunks", return_value={}) as mock_fetch,
    ):
        hybrid_search("question", expand_neighbors=True)

    requested_ids = set(mock_fetch.call_args[0][0])
    assert "doc::sec::0" not in requested_ids
    assert "doc::sec::1" not in requested_ids
