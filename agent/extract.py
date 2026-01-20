# source selection / note extraction

from .state import Source, Note, SearchResult
from .search import extract_domain

def select_sources(
    search_results: list[SearchResult],
    max_sources: int = 8,
    min_unique_domains: int = 4,
) -> list[Source]:
    """
    selects / deduplicates sources from search results
    ensures domain diversity / cap total sources
    """

    seen_urls: set[str] = set()
    seen_domains: dict[str, int] = {}
    sources: list[Source] = []

    # flatten results
    all_results: list[tuple[str, dict]] = []
    for sr in search_results:
        sr.get("results") or []
        for result in sr["results"]:
            all_results.append((sr["query"], result))
    
    # First pass: ensure domain diversity
    for query, result in all_results:
        url = result.get("url", "")
        if not url or url in seen_urls:
            continue

        domain = extract_domain(url)
        domain_count = seen_domains.get(domain, 0)

        # skip if we have too many from this domain and haven't hit min unique

        if (domain_count >= 2 and len(seen_domains) < min_unique_domains):
            continue
        seen_urls.add(url)
        seen_domains[domain] = domain_count + 1

        sources.append(Source(
            url=url,
            title=result.get("title", "Unititled"),
            domain=domain,
            snippet=result.get("content", "")[:500],
        ))

        if len(sources) == max_sources:
            break

    return sources

def format_notes_for_report(notes: list[Note], sources: list[Source]) -> str:
    # format notes for the report writer prompts

    url_to_idx = {s["url"]: i + 1 for i, s in enumerate(sources)}

    formatted_parts = []
    for note in notes:
        idx = url_to_idx.get(note["source_url"], "?")
        bullets = "\n".join(f"  - {b}" for b in note["bullets"])
        quote_line = f'  Quote: "{note["quote"]}"' if note["quote"] else ""

        formatted_parts.append(
            f"[{idx}] {note['source_url']}\n"
            f"  Relevance: {note['relevance']}\n"
            f"{bullets}\n"
            f"{quote_line}"
        )

    return "\n\n".join(formatted_parts)

def formatted_sources_list(sources: list[Source]) -> str:
    # format sources as numbered list
    lines = []
    for i, source in enumerate(sources, 1):
        lines.append(f"[{i}] {source['title']} - {source['url']}")
    return "\n".join(lines)