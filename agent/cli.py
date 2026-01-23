# CLI entry point for the Deep Research Agent.

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv


def main():
    # Load environment variables from .env at repo root
    load_dotenv()
    
    parser = argparse.ArgumentParser(
        description="Deep Research Agent - LangGraph-based research with CoVe verification"
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="Research query (or use --interactive)",
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run in interactive mode",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o",
        help="Model for drafting (default: gpt-4o)",
    )
    parser.add_argument(
        "--verify-model",
        default="gpt-4o-mini",
        help="Model for verification (default: gpt-4o-mini)",
    )
    parser.add_argument(
        "--search-provider",
        choices=["tavily", "stub"],
        default="tavily",
        help="Search provider (default: tavily)",
    )
    parser.add_argument(
        "--max-searches",
        type=int,
        default=6,
        help="Max search queries (default: 6)",
    )
    parser.add_argument(
        "--max-sources",
        type=int,
        default=8,
        help="Max sources to use (default: 8)",
    )
    parser.add_argument(
        "--cove",
        action="store_true",
        help="Enable CoVe verification layer (adds ~5 extra searches)",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output file path (default: stdout)",
    )
    parser.add_argument(
        "--report-style",
        choices=["default", "executive", "academic", "bullet"],
        default="default",
        help="Report style/format (default, executive, academic, or bullet)",
    )
    
    args = parser.parse_args()
    
    # Import here to avoid loading heavy deps before env is set
    from agent import run_research
    
    if args.interactive:
        print("Deep Research Agent (interactive mode)")
        print("Enter your research query (Ctrl+D to exit):\n")
        try:
            query = input("> ").strip()
        except EOFError:
            print("\nExiting.")
            sys.exit(0)
    elif args.query:
        query = args.query
    else:
        parser.print_help()
        sys.exit(1)
    
    print(f"\nResearching: {query}\n")
    print("=" * 60)
    
    try:
        result = run_research(
            query=query,
            draft_model=args.model,
            verify_model=args.verify_model,
            search_provider=args.search_provider,
            max_searches=args.max_searches,
            max_sources=args.max_sources,
            enable_cove=args.cove,
            report_style=args.report_style,
        )
        
        report = result.get("report") or result.get("report_draft") or "No report generated"
        
        if args.output:
            Path(args.output).write_text(report)
            print(f"\nReport saved to: {args.output}")
        else:
            print(report)
        
        # Print summary stats
        print("\n" + "=" * 60)
        print(f"Sources used: {len(result.get('sources', []))}")
        print(f"Searches run: {len(result.get('search_results', []))}")
        if result.get("verification_results"):
            confirmed = sum(1 for c in result["verification_results"] if c["status"] == "confirmed")
            print(f"Claims verified: {confirmed}/{len(result['verification_results'])}")
        
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()