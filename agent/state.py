"""
State def. for the Deep Research Agent

defines the typed state flowing from LangGraph pipeline

nodes read from / write to this state making the graph inspectable & studio accessible
"""

from typing import TypedDict, Annotated, Literal
from operator import add


class Source(TypedDict):
    # normalized source with metadata
    url: str
    title: str
    domain: str
    snippet: str

class Note(TypedDict):
    # extracted factual notes from a source
    source_url: str
    bullets: list[str]
    quote: str | None
    relevance: str

class SearchResult(TypedDict):
    # raw search result from web search
    query: str
    results: list[dict]

class VerificationClaim(TypedDict):
    # claim to verify in CoVe pipeline
    claim: str
    source_in_draft: str
    verification_query: str
    evidence: list[str] | None
    status: Literal["pending", "confirmed", "mixed", "insufficient"] | None

class VerificationSpec(TypedDict, total=False):
    # output from CoVe prompt compiler
    claims: list[VerificationClaim]
    verification_focus: str

class ResearchState(TypedDict):
    """
    Main state object that goes through research graph
    Uses Annotated[list, add] for messages to use LangGraph's auto list accumulation across nodes
    """

    # core input
    messages: Annotated[list[dict], add]
    query: str

    # planning
    plan: list[str]
    outline: list[str] | None

    # search & sources
    search_results: list[SearchResult]
    sources: list[Source]
    notes: list[Note]

    # report
    report_draft: str | None
    report: str | None

    # CoVe
    verification_spec: VerificationSpec | None
    verification_results: list[VerificationClaim] | None

    # metadata
    status: str | Literal["planning", "searching", "extracting", "drafting", "verifying", "revising", "complete", "error"]
    error: str | None
    
