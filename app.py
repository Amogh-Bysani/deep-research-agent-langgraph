# Streamlit UI for Deep Research Agent

import streamlit as st
import time
import threading
import random
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from agent import run_research

# Page config
st.set_page_config(
    page_title="Deep Research Agent",
    page_icon="🔬",
    layout="wide",
)

# Title
st.title("Deep Research Agent")
st.caption("LangGraph-powered research with optional CoVe verification")

# Rotating placeholder examples
EXAMPLE_QUERIES = [
    "What are the latest developments in quantum computing?",
    "Compare the environmental impact of electric vs hydrogen vehicles",
    "What are the key challenges in implementing AI agents in enterprise?",
    "Explain the current state of nuclear fusion research",
    "What are the pros and cons of remote work policies?",
]

# Initialize session state
if "placeholder" not in st.session_state:
    st.session_state.placeholder = random.choice(EXAMPLE_QUERIES)
if "query" not in st.session_state:
    st.session_state.query = ""
if "result" not in st.session_state:
    st.session_state.result = None
if "running" not in st.session_state:
    st.session_state.running = False

# Sidebar configuration
with st.sidebar:
    st.header("Configuration")
    
    enable_cove = st.checkbox(
        "Enable CoVe Verification",
        value=False,
        help="Adds claim verification step (~5 extra searches)"
    )
    
    report_style = st.selectbox(
        "Report Style",
        options=["default", "executive", "academic", "bullet"],
        index=0,
    )
    
    max_searches = st.slider(
        "Max Searches",
        min_value=2,
        max_value=10,
        value=6,
    )
    
    max_sources = st.slider(
        "Max Sources", 
        min_value=2,
        max_value=12,
        value=8,
    )
    
    search_provider = st.selectbox(
        "Search Provider",
        options=["tavily", "stub"],
        index=0,
        help="Use 'stub' for testing without API calls"
    )

# Main query input
query = st.text_area(
    "Research Query",
    key="query",
    height=100,
    placeholder="e.g., " + st.session_state.placeholder,
)

# Run button
col1, col2 = st.columns([1, 5])
with col1:
    run_button = st.button(
        "Run Research",
        disabled=st.session_state.running or not query.strip(),
        type="primary",
    )

# Progress phases
def get_phases(enable_cove: bool) -> list[tuple[str, float]]:
    """Return phases with estimated relative durations."""
    phases = [
        ("Planning research...", 0.10),
        ("Running searches...", 0.35),
        ("Extracting notes...", 0.25),
        ("Drafting report...", 0.20),
    ]
    if enable_cove:
        phases.extend([
            ("Compiling verification...", 0.03),
            ("Verifying claims...", 0.04),
            ("Revising report...", 0.03),
        ])
    return phases

def estimate_total_time(max_searches: int, max_sources: int, enable_cove: bool) -> float:
    """Estimate total runtime in seconds."""
    base = 10  # minimum
    search_time = max_searches * 3  # ~3s per search
    extract_time = max_sources * 2  # ~2s per extraction
    cove_time = 15 if enable_cove else 0
    return base + search_time + extract_time + cove_time

# Execute research
if run_button and query.strip():
    st.session_state.running = True
    st.session_state.result = None
    
    # Create containers
    progress_container = st.empty()
    status_container = st.empty()
    
    phases = get_phases(enable_cove)
    total_time = estimate_total_time(max_searches, max_sources, enable_cove)
    
    # Thread to run research in background
    result_holder = {"result": None, "error": None}
    
    def run_agent():
        try:
            result_holder["result"] = run_research(
                query=query.strip(),
                search_provider=search_provider,
                max_searches=max_searches,
                max_sources=max_sources,
                enable_cove=enable_cove,
                report_style=report_style,
            )
        except Exception as e:
            result_holder["error"] = str(e)
    
    # Start research thread
    thread = threading.Thread(target=run_agent)
    thread.start()
    
    # Fake progress while thread runs
    elapsed = 0.0
    phase_idx = 0
    cumulative = 0.0
    
    progress_bar = progress_container.progress(0)
    
    while thread.is_alive():
        # Update phase based on elapsed time
        target_fraction = elapsed / total_time
        
        # Find current phase
        cumulative = 0.0
        for i, (phase_name, phase_fraction) in enumerate(phases):
            cumulative += phase_fraction
            if target_fraction < cumulative:
                phase_idx = i
                break
        else:
            phase_idx = len(phases) - 1
        
        status_container.text(phases[phase_idx][0])
        progress_bar.progress(min(target_fraction, 0.95))
        
        time.sleep(0.2)
        elapsed += 0.2
    
    thread.join()
    
    # Complete progress
    progress_bar.progress(1.0)
    status_container.text("Complete!")
    time.sleep(0.3)
    
    # Clear progress indicators
    progress_container.empty()
    status_container.empty()
    
    st.session_state.running = False
    
    if result_holder["error"]:
        st.error(f"Error: {result_holder['error']}")
    else:
        st.session_state.result = result_holder["result"]
        st.rerun()

# Display results
if st.session_state.result:
    result = st.session_state.result
    report = result.get("report") or result.get("report_draft") or "No report generated"
    
    # Report section
    st.divider()
    st.subheader("Research Report")
    st.markdown(report)
    
    # Download button
    st.download_button(
        label="Download Report (.md)",
        data=report,
        file_name="research_report.md",
        mime="text/markdown",
    )
    
    # Sources section
    st.divider()
    sources = result.get("sources", [])
    with st.expander(f"Sources ({len(sources)})", expanded=False):
        for i, source in enumerate(sources, 1):
            st.markdown(f"**[{i}]** [{source.get('title', 'Untitled')}]({source.get('url', '#')})")
            st.caption(source.get("domain", ""))
    
    # Metadata footer
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Searches Run", len(result.get("search_results", [])))
    with col2:
        st.metric("Sources Used", len(sources))
    with col3:
        if result.get("verification_results"):
            confirmed = sum(1 for c in result["verification_results"] if c.get("status") == "confirmed")
            st.metric("Claims Verified", f"{confirmed}/{len(result['verification_results'])}")
        else:
            st.metric("CoVe", "Disabled")