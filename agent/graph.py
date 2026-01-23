# LangGraph Definition for Agent

import json
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END

from .state import ResearchState, Note, VerificationClaim
from .prompts import (
    PLANNER_SYSTEM, PLANNER_USER,
    EXTRACTOR_SYSTEM, EXTRACTOR_USER,
    WRITER_SYSTEM, REPORT_STYLE_HEADERS, WRITER_USER,
    COVE_COMPILER_SYSTEM, COVE_COMPILER_USER,
    COVE_REVISER_SYSTEM, COVE_REVISER_USER,
)
from .search import get_search_provider, run_search
from .extract import select_sources, format_notes_for_report, formatted_sources_list

class ResearchAgent:
    # research agent w configable models / search

    def __init__(
            self,
            draft_model: str = "gpt-4o",
            verify_model: str = "gpt-4o-mini",
            search_provider: str = "tavily",
            max_searches: int = 6,
            max_sources: int = 8,
            min_unique_domains: int = 4,
            enable_cove: bool = True,
            report_style: str = "default",
    ):
        self.draft_llm = ChatOpenAI(model=draft_model)
        self.verify_llm = ChatOpenAI(model=verify_model)
        self.search = get_search_provider(search_provider)
        self.max_searches = max_searches
        self.max_sources = max_sources
        self.min_unique_domains = min_unique_domains
        self.enable_cove = enable_cove
        self.report_style = report_style

    def plan_research(self, state: ResearchState) -> dict[str, Any]:
        messages = [
            SystemMessage(content=PLANNER_SYSTEM),
            HumanMessage(content=PLANNER_USER.format(query=state["query"])),
        ]

        response = self.draft_llm.invoke(messages)
        content = response.content if hasattr(response, 'content') else str(response)
        
        # Strip markdown code blocks if present
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        try:
            parsed = json.loads(content)
            plan = parsed.get("subquestions", [])
            outline = parsed.get("outline", [])
        except json.JSONDecodeError:
            # plaintext fallback by newline
            plan = [line.strip() for line in content.split("\n") if line.strip() and len(line.strip()) > 10]
            outline = None
        
        return {
            "plan": plan[:self.max_searches],
            "outline": outline,
            "status": "searching",
            "messages": [{"role": "assistant", "content": f"Planned {len(plan[:self.max_searches])} subquestions."}],
        }
    
    def run_searches(self, state: ResearchState) -> dict[str, Any]:
        # do web searches for subquestions
        search_results = []

        for subquestion in state["plan"]:
            result = run_search(subquestion, self.search, max_results = 5)
            search_results.append(result)
        
        return {
            "search_results": search_results,
            "status": "extracting",
            "messages": [{"role": "assistant", "content": f"Ran {len(search_results)} searches."}],
        }

    def select_and_extract(self, state: ResearchState) -> dict[str, Any]:
        sources = select_sources(
            state["search_results"],
            max_sources=self.max_sources,
            min_unique_domains=self.min_unique_domains,
        )

        notes = []
        for source in sources:
            messages = [
                SystemMessage(content=EXTRACTOR_SYSTEM),
                HumanMessage(content=EXTRACTOR_USER.format(
                    query=state["query"],
                    url=source["url"],
                    title=source["title"],
                    content=source["snippet"],
                )),
            ]

            response = self.draft_llm.invoke(messages)
            content = response.content if hasattr(response, 'content') else str(response)

            # Strip markdown code blocks if present
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            try:
                parsed = json.loads(content)
                notes.append(Note(
                    source_url=source["url"],
                    bullets=parsed.get("bullets", []),
                    quote=parsed.get("quote"),
                    relevance=parsed.get("relevance", ""),
                ))
            except json.JSONDecodeError:
                notes.append(Note(
                    source_url=source["url"],
                    bullets=[content[:500]],
                    quote=None,
                    relevance="Extraction parsing failed",
                ))
        
        return {
            "sources": sources,
            "notes": notes,
            "status": "drafting",
            "messages": [{"role": "assistant", "content": f"Extracted notes from {len(sources)} sources."}],
        }

    def draft_report(self, state: ResearchState) -> dict[str, Any]:
        # Generate the initial report draft.

        outline_str = "\n".join(state["outline"]) if state.get("outline") else "Use your judgment"
        notes_str = format_notes_for_report(state["notes"], state["sources"])
        sources_str = formatted_sources_list(state["sources"])

        # Inject report style guidance into the writer system prompt
        style = state.get("report_style", "default")
        style_header = REPORT_STYLE_HEADERS.get(style, REPORT_STYLE_HEADERS["default"])
        writer_system = WRITER_SYSTEM.format(style_header=style_header)

        messages = [
            SystemMessage(content=writer_system),
            HumanMessage(
                content=WRITER_USER.format(
                    query=state["query"],
                    outline=outline_str,
                    notes=notes_str,
                    sources=sources_str,
                )
            ),
        ]

        response = self.draft_llm.invoke(messages)
        content = response.content if hasattr(response, "content") else str(response)

        next_status = "verifying" if self.enable_cove else "complete"

        return {
            "report_style": style,  # optional: keep it in state for downstream/debugging
            "report_draft": content,
            "report": None if self.enable_cove else content,
            "status": next_status,
            "messages": [] if self.enable_cove else [{"role": "assistant", "content": content}],
        }
    
    def compile_verification(self, state: ResearchState) -> dict[str, Any]:
        # Generate verification spec using CoVe approach
        messages = [
            SystemMessage(content=COVE_COMPILER_SYSTEM),
            HumanMessage(content=COVE_COMPILER_USER.format(
                query=state["query"],
                draft=state["report_draft"],
            )),
        ]
        
        response = self.verify_llm.invoke(messages)
        content = response.content if hasattr(response, 'content') else str(response)
        
        try:
            parsed = json.loads(content)
            claims = [
                VerificationClaim(
                    claim=c["claim"],
                    source_in_draft=c.get("source_in_draft", ""),
                    verification_query=c.get("verification_query", ""),
                    evidence=None,
                    status="pending",
                )
                for c in parsed.get("claims", [])
            ]
            verification_focus = parsed.get("verification_focus", "")
        except json.JSONDecodeError:
            claims = []
            verification_focus = "Parsing failed"
        
        return {
            "verification_spec": {
                "claims": claims,
                "verification_focus": verification_focus,
            },
            "status": "verifying",
        }
    
    def verify_claims(self, state: ResearchState) -> dict[str, Any]:
        # Run verification searches for each claim.
        if not state.get("verification_spec"):
            return {"verification_results": [], "status": "revising"}
        
        claims = state["verification_spec"]["claims"]
        verified_claims = []
        
        for claim in claims[:5]:  # Cap verification searches
            result = run_search(claim["verification_query"], self.search, max_results=3)
            
            evidence = [
                r.get("content", "")[:200] 
                for r in result["results"]
            ]
            
            # Simple heuristic: if any evidence mentions similar terms, mark as confirmed
            claim_lower = claim["claim"].lower()
            matches = sum(1 for e in evidence if any(
                word in e.lower() 
                for word in claim_lower.split()[:5]
            ))
            
            if matches >= 2:
                status = "confirmed"
            elif matches == 1:
                status = "mixed"
            else:
                status = "insufficient"
            
            verified_claims.append(VerificationClaim(
                claim=claim["claim"],
                source_in_draft=claim["source_in_draft"],
                verification_query=claim["verification_query"],
                evidence=evidence,
                status=status,
            ))
        
        return {
            "verification_results": verified_claims,
            "status": "revising",
        }
    
    def revise_report(self, state: ResearchState) -> dict[str, Any]:
        # Produce final report incorporating verification results.
        verification_str = json.dumps(
            [
                {
                    "claim": c["claim"],
                    "status": c["status"],
                    "evidence_snippets": c["evidence"][:2] if c["evidence"] else [],
                }
                for c in (state.get("verification_results") or [])
            ],
            indent=2,
        )
        
        messages = [
            SystemMessage(content=COVE_REVISER_SYSTEM),
            HumanMessage(content=COVE_REVISER_USER.format(
                query=state["query"],
                draft=state["report_draft"],
                verification_results=verification_str,
            )),
        ]
        
        response = self.draft_llm.invoke(messages)
        content = response.content if hasattr(response, 'content') else str(response)
        
        return {
            "report": content,
            "status": "complete",
            "messages": [{"role": "assistant", "content": content}],
        }


def build_graph(
    draft_model: str = "gpt-4o",
    verify_model: str = "gpt-4o-mini",
    search_provider: str = "tavily",
    max_searches: int = 6,
    max_sources: int = 8,
    min_unique_domains: int = 4,
    enable_cove: bool = True,
    report_style: str = "default",
) -> StateGraph:
    # Build and return the research agent graph
    
    agent = ResearchAgent(
        draft_model=draft_model,
        verify_model=verify_model,
        search_provider=search_provider,
        max_searches=max_searches,
        max_sources=max_sources,
        min_unique_domains=min_unique_domains,
        enable_cove=enable_cove,
        report_style=report_style,
    )
    
    # Create graph
    graph = StateGraph(ResearchState)
    
    # Add nodes
    graph.add_node("plan_research", agent.plan_research)
    graph.add_node("run_searches", agent.run_searches)
    graph.add_node("select_and_extract", agent.select_and_extract)
    graph.add_node("draft_report", agent.draft_report)
    
    if enable_cove:
        graph.add_node("compile_verification", agent.compile_verification)
        graph.add_node("verify_claims", agent.verify_claims)
        graph.add_node("revise_report", agent.revise_report)
    
    # Add edges; baseline flow
    graph.add_edge(START, "plan_research")
    graph.add_edge("plan_research", "run_searches")
    graph.add_edge("run_searches", "select_and_extract")
    graph.add_edge("select_and_extract", "draft_report")
    
    if enable_cove:
        # CoVe verification flow
        graph.add_edge("draft_report", "compile_verification")
        graph.add_edge("compile_verification", "verify_claims")
        graph.add_edge("verify_claims", "revise_report")
        graph.add_edge("revise_report", END)
    else:
        graph.add_edge("draft_report", END)
    
    return graph.compile()


def run_research(
    query: str,
    **config_kwargs,
) -> ResearchState:
    # Convenience function to run research on a query.
    graph = build_graph(**config_kwargs)
    
    initial_state: ResearchState = {
        "messages": [{"role": "user", "content": query}],
        "query": query,
        "plan": [],
        "outline": None,
        "search_results": [],
        "sources": [],
        "notes": [],
        "report_draft": None,
        "report": None,
        "verification_spec": None,
        "verification_results": None,
        "status": "planning",
        "error": None,
        "report_style": config_kwargs.get("report_style", "default"),
    }
    
    final_state = graph.invoke(initial_state)
    return final_state