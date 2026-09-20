from unittest.mock import MagicMock, patch

from src.retrieval.rerank import rerank_chunks


def _chunk(chunk_id, text):
    return {"chunk_id": chunk_id, "chunk_text": text}


def _mock_response(scores: list[float]) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.json.return_value = [[{"label": "LABEL_0", "score": s} for s in scores]]
    return mock_resp


def test_rerank_chunks_returns_empty_for_no_candidates():
    with patch("src.retrieval.rerank.requests.post") as mock_post:
        results = rerank_chunks("question", [], top_n=5)
    mock_post.assert_not_called()
    assert results == []


def test_rerank_chunks_sorts_by_score_and_maps_back_to_original_chunks():
    chunks = [_chunk("a", "text a"), _chunk("b", "text b"), _chunk("c", "text c")]
    # HF returns scores in the same order the pairs were submitted
    with patch("src.retrieval.rerank.requests.post", return_value=_mock_response([0.3, 0.9, 0.1])):
        results = rerank_chunks("question", chunks, top_n=2)

    assert [r["chunk_id"] for r in results] == ["b", "a"]
    assert results[0]["rerank_score"] == 0.9
    assert results[1]["rerank_score"] == 0.3


def test_rerank_chunks_sends_question_and_chunk_text_as_pairs():
    chunks = [_chunk("a", "text a"), _chunk("b", "text b")]
    with patch("src.retrieval.rerank.requests.post", return_value=_mock_response([0.5, 0.5])) as mock_post:
        rerank_chunks("what is the risk", chunks, top_n=5)

    call_kwargs = mock_post.call_args.kwargs
    assert call_kwargs["json"] == {
        "inputs": [
            {"text": "what is the risk", "text_pair": "text a"},
            {"text": "what is the risk", "text_pair": "text b"},
        ]
    }


def test_rerank_chunks_sends_bearer_auth_header():
    chunks = [_chunk("a", "text a")]
    with patch("src.retrieval.rerank.requests.post", return_value=_mock_response([0.5])) as mock_post:
        rerank_chunks("question", chunks, top_n=5)

    headers = mock_post.call_args.kwargs["headers"]
    assert headers["Authorization"].startswith("Bearer ")


def test_rerank_chunks_top_n_limits_results_even_when_more_candidates_score_well():
    chunks = [_chunk("a", "text a"), _chunk("b", "text b"), _chunk("c", "text c")]
    with patch("src.retrieval.rerank.requests.post", return_value=_mock_response([0.9, 0.8, 0.7])):
        results = rerank_chunks("question", chunks, top_n=1)

    assert len(results) == 1
    assert results[0]["chunk_id"] == "a"
