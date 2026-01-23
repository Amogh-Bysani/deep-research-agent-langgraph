"""
Smoke tests - does the graph run without crashing?
"""

import pytest


def test_graph_builds():
    """Graph compiles without error."""
    from agent.graph import build_graph
    
    graph = build_graph(search_provider="stub", enable_cove=False)
    assert graph is not None


def test_graph_builds_with_cove():
    """Graph compiles with CoVe enabled."""
    from agent.graph import build_graph
    
    graph = build_graph(search_provider="stub", enable_cove=True)
    assert graph is not None


def test_run_research_stub():
    """Full pipeline runs with stub search."""
    from agent.graph import run_research
    
    result = run_research(
        query="What is the capital of France?",
        search_provider="stub",
        enable_cove=False,
    )
    
    assert result["status"] == "complete"
    assert result["report"] is not None
    assert len(result["sources"]) > 0


def test_run_research_with_cove_stub():
    """Full pipeline with CoVe runs with stub search."""
    from agent.graph import run_research
    
    result = run_research(
        query="What is machine learning?",
        search_provider="stub",
        enable_cove=True,
    )
    
    assert result["status"] == "complete"
    assert result["report"] is not None


def test_all_report_styles():
    """All report styles run without error."""
    from agent.graph import run_research
    
    styles = ["default", "executive", "academic", "bullet"]
    
    for style in styles:
        result = run_research(
            query="Test query",
            search_provider="stub",
            enable_cove=False,
            report_style=style,
        )
        assert result["status"] == "complete"
        assert result["report"] is not None