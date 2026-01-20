"""
Web Search Functionality

Tavily with stub fallback

"""

import os
from typing import Protocol, runtime_checkable

from .state import SearchResult

@runtime_checkable
class SearchProvider(Protocol):
    # protocol for search providers
    def search(self, query: str, max_results: int = 5) -> list[dict]: ...

class TavilySearch:
    # tavily search provider

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        if not self.api_key:
            raise ValueError("TAVILY_API_KEY required")
        
        from tavily import TavilyClient
        self.client = TavilyClient(api_key=self.api_key)

    def search(self, query: str, max_results: int = 5) -> list[dict]:
        # run a tavily search
        # print(f"Query: {query}")
        response = self.client.search(
            query=query,
            max_results=max_results,
            include_raw_content=False,
        )
        # print(f"Response: {response}")
        return response.get("results") or []

class StubSearch:
    """Stub search for testing without API calls."""

    def search(self, query: str, max_results: int = 5) -> list[dict]:
        # return fake results for testing
        return [
            {
                "url": f"https://example.com/result-{i}",
                "title": f"Stub Result {i} for: {query[:30]}",
                "content": f"This is stub content for result {i}. "
                            f"It contains information about {query}. "
                            f"In a real search this would be real content.",
                "raw_content": f"Extended stub content for {query}...",
            }
            for i in range(1, min(max_results + 1, 4))
        ]
    
def get_search_provider(provider: str = "tavily") -> SearchProvider:
    # pull search provider
    if provider == "stub":
        return StubSearch()
    elif provider == "tavily":
        return TavilySearch()
    else:
        raise ValueError(f"Unknown search provider: {provider}")
    
def run_search(query: str, provider: SearchProvider, max_results: int = 5) -> SearchResult:
    # Run a single search & return structured result
    results = provider.search(query, max_results=max_results)
    return SearchResult(query=query, results=results or [])

def extract_domain(url: str) -> str:
    # extract domain from URL
    from urllib.parse import urlparse
    parsed = urlparse(url)
    domain = parsed.netloc
    if domain.startswith("www."):
        domain = domain[4:]
    return domain