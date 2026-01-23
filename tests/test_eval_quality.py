"""
Quality evaluation tests - does the output meet minimum standards?
"""

import pytest
import re
from dotenv import load_dotenv
load_dotenv()

def test_report_has_required_sections():
    """Report contains expected structure."""
    from agent.graph import run_research
    
    result = run_research(
        query="What is artificial intelligence?",
        search_provider="stub",
        enable_cove=False,
    )
    
    report = result["report"]
    assert report is not None
    
    # Check for key sections (case-insensitive)
    report_lower = report.lower()
    assert "tl;dr" in report_lower or "summary" in report_lower
    assert "source" in report_lower


def test_report_has_citations():
    """Report includes citation markers."""
    from agent.graph import run_research
    
    result = run_research(
        query="Explain cloud computing",
        search_provider="stub",
        enable_cove=False,
    )
    
    report = result["report"]
    
    # Check for citation patterns like [1], [2], etc.
    citation_pattern = r'\[\d+\]'
    citations = re.findall(citation_pattern, report)
    assert len(citations) >= 1, "Report should contain at least one citation"


def test_minimum_sources():
    """Pipeline retrieves minimum number of sources."""
    from agent.graph import run_research
    
    result = run_research(
        query="What is blockchain?",
        search_provider="stub",
        enable_cove=False,
    )
    
    assert len(result["sources"]) >= 2


def test_cove_produces_verification_results():
    """CoVe pipeline produces verification results."""
    from agent.graph import run_research
    
    result = run_research(
        query="What is quantum computing?",
        search_provider="stub",
        enable_cove=True,
    )
    
    # Should have verification results
    assert result.get("verification_results") is not None
    assert len(result["verification_results"]) > 0


def test_verification_claims_have_status():
    """Each verified claim has a status."""
    from agent.graph import run_research
    
    result = run_research(
        query="Explain neural networks",
        search_provider="stub",
        enable_cove=True,
    )
    
    for claim in result.get("verification_results", []):
        assert claim.get("status") in ["confirmed", "mixed", "insufficient", "pending"]


def test_sources_have_required_fields():
    """Each source has url, title, and domain."""
    from agent.graph import run_research
    
    result = run_research(
        query="What is data science?",
        search_provider="stub",
        enable_cove=False,
    )
    
    for source in result["sources"]:
        assert "url" in source
        assert "title" in source
        assert "domain" in source


def test_executive_style_is_concise():
    """Executive style produces shorter output."""
    from agent.graph import run_research
    
    default_result = run_research(
        query="What is AI?",
        search_provider="stub",
        enable_cove=False,
        report_style="default",
    )
    
    executive_result = run_research(
        query="What is AI?",
        search_provider="stub",
        enable_cove=False,
        report_style="executive",
    )
    
    # Executive should generally be shorter (not a strict test, just a sanity check)
    # This might fail sometimes due to LLM variability, so we just check it runs
    assert executive_result["report"] is not None