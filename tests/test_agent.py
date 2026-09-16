import json
from unittest.mock import MagicMock, patch

from src.agent.graph import (
    NO_INFO_RESPONSE,
    _documents_retrieved,
    _has_no_grounding,
    answer_question,
    hybrid_node,
    router_node,
    sql_node,
    synthesis_node,
)


def _state(**overrides):
    base = {
        "question": "test question",
        "use_hybrid": False,
        "hybrid_company": None,
        "use_sql": False,
        "sql_queries": [],
        "hybrid_results": [],
        "sql_results": [],
        "tool_calls": [],
        "answer": "",
    }
    base.update(overrides)
    return base


# --- router_node -------------------------------------------------------


def test_router_node_applies_the_llm_routing_decision():
    decision = {
        "use_hybrid_search": True,
        "hybrid_search_company": "Apple",
        "use_sql_tool": True,
        "sql_queries": [{"company": "Apple", "year": 2025, "metric": "revenue"}],
    }
    with patch("src.agent.graph.route", return_value=decision):
        state = router_node(_state())
    assert state["use_hybrid"] is True
    assert state["hybrid_company"] == "Apple"
    assert state["use_sql"] is True
    assert state["sql_queries"] == decision["sql_queries"]


# --- hybrid_node / sql_node ---------------------------------------------


def test_hybrid_node_skips_search_and_logs_no_tool_when_router_says_no():
    with patch("src.agent.graph.hybrid_search") as mock_search:
        state = hybrid_node(_state(use_hybrid=False))
    mock_search.assert_not_called()
    assert state["hybrid_results"] == []
    assert "hybrid_search" not in state["tool_calls"]


def test_hybrid_node_calls_search_and_logs_the_tool_when_router_says_yes():
    with patch("src.agent.graph.hybrid_search", return_value=[{"chunk_text": "x"}]) as mock_search:
        state = hybrid_node(_state(use_hybrid=True))
    mock_search.assert_called_once()
    assert state["hybrid_results"] == [{"chunk_text": "x"}]
    assert "hybrid_search" in state["tool_calls"]


def test_hybrid_node_passes_the_router_company_filter_through():
    """The index holds multiple companies' filings together -- an unfiltered
    search can surface another company's similarly-worded risk factors
    instead of the one actually asked about. hybrid_node must forward
    whatever company the router identified.
    """
    with patch("src.agent.graph.hybrid_search", return_value=[]) as mock_search:
        hybrid_node(_state(use_hybrid=True, hybrid_company="Apple"))
    mock_search.assert_called_once_with("test question", top_k=5, company="Apple")


def test_hybrid_node_passes_none_when_router_found_no_single_company():
    with patch("src.agent.graph.hybrid_search", return_value=[]) as mock_search:
        hybrid_node(_state(use_hybrid=True, hybrid_company=None))
    mock_search.assert_called_once_with("test question", top_k=5, company=None)


def test_sql_node_skips_lookup_when_router_says_no():
    with patch("src.agent.graph.query_financials") as mock_query:
        state = sql_node(_state(use_sql=False, sql_queries=[{"company": "Apple", "year": 2025, "metric": "revenue"}]))
    mock_query.assert_not_called()
    assert state["sql_results"] == []
    assert "sql_tool" not in state["tool_calls"]


def test_sql_node_looks_up_every_requested_metric():
    queries = [
        {"company": "Apple", "year": 2025, "metric": "revenue"},
        {"company": "Apple", "year": 2025, "metric": "net_income"},
    ]
    with patch("src.agent.graph.query_financials", side_effect=[{"metric_value": 1}, {"metric_value": 2}]) as mock_query:
        state = sql_node(_state(use_sql=True, sql_queries=queries))
    assert mock_query.call_count == 2
    assert state["sql_results"] == [{"metric_value": 1}, {"metric_value": 2}]
    assert "sql_tool" in state["tool_calls"]


# --- _has_no_grounding ---------------------------------------------------


def test_no_grounding_when_router_picked_neither_tool():
    assert _has_no_grounding(_state(use_hybrid=False, use_sql=False)) is True


def test_no_grounding_when_hybrid_used_but_empty_and_sql_unused():
    assert _has_no_grounding(_state(use_hybrid=True, hybrid_results=[], use_sql=False)) is True


def test_grounded_when_hybrid_found_something():
    assert _has_no_grounding(_state(use_hybrid=True, hybrid_results=[{"chunk_text": "x"}])) is False


def test_grounded_when_sql_found_at_least_one_real_metric():
    state = _state(use_sql=True, sql_results=[None, {"metric_value": 1}])
    assert _has_no_grounding(state) is False


def test_no_grounding_when_sql_used_but_every_metric_came_back_none():
    state = _state(use_sql=True, sql_results=[None, None])
    assert _has_no_grounding(state) is True


# --- synthesis_node -------------------------------------------------------


def test_synthesis_skips_the_llm_call_when_nothing_was_found():
    with patch("src.agent.graph.OpenAI") as mock_openai:
        state = synthesis_node(_state(use_hybrid=True, hybrid_results=[]))
    mock_openai.assert_not_called()
    assert state["answer"] == NO_INFO_RESPONSE


def test_synthesis_calls_the_llm_and_uses_its_answer_when_grounded():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "The answer is 42."
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    state = _state(
        use_hybrid=True,
        hybrid_results=[{"company": "Apple", "year": 2025, "section": "Item 1A", "chunk_text": "risk text"}],
    )
    with patch("src.agent.graph.OpenAI", return_value=mock_client):
        result = synthesis_node(state)

    assert result["answer"] == "The answer is 42."
    mock_client.chat.completions.create.assert_called_once()


def test_synthesis_prompt_frames_filing_excerpts_as_untrusted():
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "answer"
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    state = _state(
        use_hybrid=True,
        hybrid_results=[{"company": "Apple", "year": 2025, "section": "Item 1A", "chunk_text": "risk text"}],
    )
    with patch("src.agent.graph.OpenAI", return_value=mock_client):
        synthesis_node(state)

    prompt = mock_client.chat.completions.create.call_args.kwargs["messages"][0]["content"]
    assert "untrusted" in prompt.lower()
    assert "risk text" in prompt


# --- full graph wiring (all four documented paths) ------------------------


def _run_graph(decision, hybrid_return=None, sql_return=None, llm_answer="the answer"):
    mock_response = MagicMock()
    mock_response.choices[0].message.content = llm_answer
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with (
        patch("src.agent.graph.route", return_value=decision),
        patch("src.agent.graph.hybrid_search", return_value=hybrid_return or []),
        patch("src.agent.graph.query_financials", return_value=sql_return),
        patch("src.agent.graph.OpenAI", return_value=mock_client),
        patch("src.agent.graph.get_snowflake_connection"),
    ):
        return answer_question("some question")


def test_unstructured_only_path_calls_only_hybrid_search():
    decision = {
        "use_hybrid_search": True,
        "hybrid_search_company": "Apple",
        "use_sql_tool": False,
        "sql_queries": [],
    }
    result = _run_graph(decision, hybrid_return=[{"company": "Apple", "year": 2025, "section": "Item 1A", "chunk_text": "x"}])
    assert result["tool_calls"] == ["hybrid_search"]
    assert result["answer"] == "the answer"


def test_structured_only_path_calls_only_sql_tool():
    decision = {
        "use_hybrid_search": False,
        "hybrid_search_company": None,
        "use_sql_tool": True,
        "sql_queries": [{"company": "Apple", "year": 2025, "metric": "revenue"}],
    }
    result = _run_graph(decision, sql_return={"metric_value": 416161000000, "unit": "USD", "metric_name": "revenue", "company": "Apple", "year": 2025, "source": "x"})
    assert result["tool_calls"] == ["sql_tool"]
    assert result["answer"] == "the answer"


def test_combined_path_calls_both_tools():
    decision = {
        "use_hybrid_search": True,
        "hybrid_search_company": "Apple",
        "use_sql_tool": True,
        "sql_queries": [{"company": "Apple", "year": 2025, "metric": "net_income"}],
    }
    result = _run_graph(
        decision,
        hybrid_return=[{"company": "Apple", "year": 2025, "section": "Item 1A", "chunk_text": "x"}],
        sql_return={"metric_value": 1, "unit": "USD", "metric_name": "net_income", "company": "Apple", "year": 2025, "source": "x"},
    )
    assert set(result["tool_calls"]) == {"hybrid_search", "sql_tool"}
    assert result["answer"] == "the answer"


def test_no_match_path_calls_no_tools_and_returns_fixed_response():
    decision = {
        "use_hybrid_search": False,
        "hybrid_search_company": None,
        "use_sql_tool": False,
        "sql_queries": [],
    }
    result = _run_graph(decision)
    assert result["tool_calls"] == []
    assert result["answer"] == NO_INFO_RESPONSE


# --- _documents_retrieved ---------------------------------------------------


def test_documents_retrieved_keeps_metadata_and_drops_chunk_text():
    hybrid_results = [
        {
            "chunk_id": "aapl::item1a::3",
            "company": "Apple",
            "year": 2025,
            "section": "Item 1A",
            "chunk_text": "long filing text that shouldn't end up in the log",
            "rrf_score": 0.5,
            "is_neighbor": False,
        },
        {
            "chunk_id": "aapl::item1a::4",
            "company": "Apple",
            "year": 2025,
            "section": "Item 1A",
            "chunk_text": "neighbor text",
            "rrf_score": None,
            "is_neighbor": True,
        },
    ]
    docs = _documents_retrieved(hybrid_results)
    assert docs == [
        {"chunk_id": "aapl::item1a::3", "company": "Apple", "year": 2025, "section": "Item 1A", "is_neighbor": False},
        {"chunk_id": "aapl::item1a::4", "company": "Apple", "year": 2025, "section": "Item 1A", "is_neighbor": True},
    ]
    assert "chunk_text" not in json.dumps(docs)


def test_documents_retrieved_empty_when_no_hybrid_results():
    assert _documents_retrieved([]) == []


# --- query_log observability -------------------------------------------------


def test_log_query_records_documents_retrieved_and_sql_params_used():
    """query_log should capture which chunks grounded the answer and which
    exact (company, year, metric) params sql_tool was called with -- not just
    that hybrid_search/sql_tool ran."""
    decision = {
        "use_hybrid_search": True,
        "hybrid_search_company": "Apple",
        "use_sql_tool": True,
        "sql_queries": [{"company": "Apple", "year": 2025, "metric": "net_income"}],
    }
    hybrid_return = [
        {
            "chunk_id": "aapl::item1a::3",
            "company": "Apple",
            "year": 2025,
            "section": "Item 1A",
            "chunk_text": "x",
            "is_neighbor": False,
        }
    ]
    sql_return = {
        "metric_value": 1,
        "unit": "USD",
        "metric_name": "net_income",
        "company": "Apple",
        "year": 2025,
        "source": "x",
    }

    mock_response = MagicMock()
    mock_response.choices[0].message.content = "the answer"
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    with (
        patch("src.agent.graph.route", return_value=decision),
        patch("src.agent.graph.hybrid_search", return_value=hybrid_return),
        patch("src.agent.graph.query_financials", return_value=sql_return),
        patch("src.agent.graph.OpenAI", return_value=mock_client),
        patch("src.agent.graph.get_snowflake_connection", return_value=mock_conn),
    ):
        answer_question("some question")

    sql_text, params = mock_cursor.execute.call_args[0]
    assert "documents_retrieved" in sql_text
    assert "sql_queries_used" in sql_text
    assert json.loads(params[3]) == [
        {"chunk_id": "aapl::item1a::3", "company": "Apple", "year": 2025, "section": "Item 1A", "is_neighbor": False}
    ]
    assert json.loads(params[4]) == [{"company": "Apple", "year": 2025, "metric": "net_income"}]


def test_log_query_records_empty_sql_params_when_router_skipped_sql():
    decision = {
        "use_hybrid_search": True,
        "hybrid_search_company": "Apple",
        "use_sql_tool": False,
        "sql_queries": [],
    }
    hybrid_return = [
        {"chunk_id": "c1", "company": "Apple", "year": 2025, "section": "Item 1A", "chunk_text": "x", "is_neighbor": False}
    ]

    mock_response = MagicMock()
    mock_response.choices[0].message.content = "the answer"
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    with (
        patch("src.agent.graph.route", return_value=decision),
        patch("src.agent.graph.hybrid_search", return_value=hybrid_return),
        patch("src.agent.graph.query_financials") as mock_query,
        patch("src.agent.graph.OpenAI", return_value=mock_client),
        patch("src.agent.graph.get_snowflake_connection", return_value=mock_conn),
    ):
        answer_question("some question")

    mock_query.assert_not_called()
    params = mock_cursor.execute.call_args[0][1]
    assert json.loads(params[4]) == []
