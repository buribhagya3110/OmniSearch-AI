import time
from typing import Dict, Any
from search import SearchEngine
from retrieval import ResultRetriever
from ui.result_display import render_result_card

def render_search_page(st):
    """Renders the search query interface and retrieved results."""
    st.header("🔍 Intelligent Multi-Modal Search")
    st.caption("Search across all indexed documents using Hybrid, Semantic, Keyword, or Exact Match.")

    search_engine = SearchEngine()
    retriever = ResultRetriever()

    # Search Bar & Mode Selection
    col_query, col_mode = st.columns([3, 1])

    with col_query:
        query = st.text_input(
            "Enter your search query",
            placeholder="e.g. quantum computing algorithms, python error handling, medical report",
            label_visibility="collapsed"
        )

    with col_mode:
        search_mode = st.selectbox(
            "Search Mode",
            options=["hybrid", "semantic", "keyword", "exact"],
            format_func=lambda x: {
                "hybrid": "⚡ Hybrid (BM25 + FAISS)",
                "semantic": "🧠 Semantic (FAISS)",
                "keyword": "🔤 Keyword (BM25)",
                "exact": "🎯 Exact Match"
            }.get(x, x),
            label_visibility="collapsed"
        )

    # Sidebar Filter Controls
    st.sidebar.subheader("⚙️ Search Filters & Weights")
    category_filter = st.sidebar.selectbox(
        "Filter by File Type",
        options=["all", "pdf", "docx", "pptx", "image", "audio", "video", "code"],
        format_func=lambda x: x.upper() if x != "all" else "All Formats"
    )

    top_k = st.sidebar.slider("Max Results (Top-K)", min_value=1, max_value=50, value=10)
    min_score = st.sidebar.slider("Minimum Relevance Threshold", min_value=0.0, max_value=1.0, value=0.50, step=0.05)

    bm25_weight = 0.5
    semantic_weight = 0.5
    if search_mode == "hybrid":
        st.sidebar.markdown("**Hybrid Score Weighting:**")
        bm25_weight = st.sidebar.slider("BM25 Keyword Weight", 0.0, 1.0, 0.5, step=0.1)
        semantic_weight = st.sidebar.slider("FAISS Semantic Weight", 0.0, 1.0, 0.5, step=0.1)

    if query:
        start_time = time.time()

        # Execute Search
        search_output = search_engine.search(
            query=query,
            mode=search_mode,
            category=None if category_filter == "all" else category_filter,
            top_k=top_k,
            bm25_weight=bm25_weight,
            semantic_weight=semantic_weight,
            min_score=min_score
        )

        elapsed_ms = (time.time() - start_time) * 1000

        # Query Processing Feedback
        proc = search_output.get("processed_query", {})
        if proc.get("has_spelling_correction"):
            corrected = proc.get("corrected_query")
            st.info(f"💡 Did you mean: **{corrected}**?")

        expansions = proc.get("expanded_terms", [])
        if expansions:
            st.markdown(f"🏷️ *Related concepts:* {', '.join(expansions[:6])}")

        # Retrieve & Enrich Results
        results = retriever.retrieve_results(search_output, fetch_similar=True)

        # Summary Bar
        st.markdown(
            f"Found **{len(results)}** match(es) in **{elapsed_ms:.1f} ms** "
            f"using **{search_mode.upper()}** mode."
        )
        st.markdown("---")

        if not results:
            st.warning("No matching documents found. Try adjusting keywords, switching search modes, or lowering the score threshold.")
        else:
            for idx, item in enumerate(results):
                render_result_card(st, item, idx)
