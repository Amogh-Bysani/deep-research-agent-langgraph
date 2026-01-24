# deep-research-agent-langgraph
A LangGraph-based deep research agent that performs multi-step web research and produces structured, source-grounded reports.
---

## Features

- **Web-grounded research** using search APIs (Tavily or stub mode)
- **Explicit LangGraph pipeline** for planning, searching, extraction, writing, and verification
- **Optional CoVe (Chain-of-Verification)** layer for claim checking
- **Multiple report styles** (`default`, `executive`, `academic`, `bullet`)
- **CLI interface** for fast iteration
- **Minimal Streamlit UI** for interactive usage
- **LangSmith tracing support** for debugging and inspection
- **Stub search provider** for testing without API calls

---

## High-Level Flow
plan → search → extract → draft → (optional) verify → revise

Each step reads from and writes to an explicit shared state, making the pipeline easy to debug, modify, and extend.

---
## Installation

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/deep-research-agent-langgraph.git
cd deep-research-agent-langgraph
```

### 2. Create a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -e .
```

## Environment Variables

Create a `.env` file in the project root by copying the example:
```bash
cp .env.example .env
```

Fill in the required keys:
```env
OPENAI_API_KEY=your_openai_key
TAVILY_API_KEY=your_tavily_key        # optional if using stub mode
LANGCHAIN_API_KEY=your_langsmith_key  # optional
LANGCHAIN_TRACING_V2=true             # optional
LANGCHAIN_PROJECT=deep-research-agent # optional
```

**Notes:**
- Tavily is optional if you use `--search-provider stub`
- LangSmith is optional but recommended for debugging and graph inspection

## CLI Usage

Run a research query directly from the command line:
```bash
research "What are the latest developments in quantum computing?"
```

### Common options
```bash
research "Your query here" \
  --search-provider tavily \
  --max-searches 6 \
  --max-sources 8 \
  --style executive \
  --cove
```

### Available flags

| Flag | Description |
|------|-------------|
| `--search-provider {tavily, stub}` | Search backend to use |
| `--max-searches N` | Maximum number of search queries |
| `--max-sources N` | Maximum sources to include |
| `--style {default, executive, academic, bullet}` | Report format style |
| `--cove` | Enable CoVe verification layer |
| `--output report.md` | Save report to file |
| `--interactive` | Prompt for input |

## Streamlit UI

To run the minimal web UI:
```bash
python -m streamlit run app.py
```

The UI allows you to:
- Enter research queries
- Configure search limits and report style
- Enable/disable CoVe verification
- View and download generated reports
- Inspect sources and metadata

> **Note:** The progress bar is intentionally simulated to avoid blocking UI responsiveness.

## Stub Search Mode (Testing)

For development and testing without API calls:
```bash
research "Test query" --search-provider stub
```

This uses static fake search results so you can iterate on prompts, structure, and formatting without external dependencies.

## LangSmith Tracing (Optional)

If LangSmith is enabled, you can:
- Inspect the LangGraph execution
- See node-by-node state transitions
- Debug prompt failures and parsing issues
- Track token usage

This is especially helpful when tuning prompts or debugging extraction errors.

## Project Structure
```
agent/
├── graph.py       # LangGraph definition
├── state.py       # Typed state definition
├── prompts.py     # All prompt templates
├── search.py      # Search provider abstraction
├── extract.py     # Source selection & formatting
└── cli.py         # CLI entry point

app.py             # Streamlit UI
tests/             # Test suite
examples/          # Sample outputs
```

## Limitations

- No explicit source authority scoring yet
- Citations are writer-managed (not programmatic)
- No automatic multi-hop follow-up searches
- Evaluations are mostly structural

These are discussed in more detail in [DESIGN.md](DESIGN.md).
