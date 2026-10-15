
import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    st = None
    HAS_STREAMLIT = False


def run_streamlit_app():
    """Run the OmniSearch AI Streamlit web application."""
    st.set_page_config(
        page_title="OmniSearch AI",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    from database.database import Database
    from ui.search_page import render_search_page
    from ui.upload_page import render_upload_page

    db = Database()
    stats = db.get_stats()

    # Sidebar
    st.sidebar.title("⚡ OmniSearch AI")
    st.sidebar.caption("Intelligent Multi-Format Document Search")

    page = st.sidebar.radio(
        "Navigation",
        options=[
            "🔍 Search",
            "📤 Upload & Index",
            "📚 Document Library",
            "📊 System Analytics"
        ]
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📈 Index Status")
    st.sidebar.metric("Indexed Documents", stats["total_documents"])
    st.sidebar.metric("Total Words", f"{stats['total_words']:,}")
    st.sidebar.metric("Storage Used", stats["total_size_formatted"])

    if page == "🔍 Search":
        render_search_page(st)

    elif page == "📤 Upload & Index":
        render_upload_page(st)

    elif page == "📚 Document Library":
        st.header("📚 Indexed Document Library")

        docs = db.list_all_documents(limit=100)

        if not docs:
            st.info(
                "No documents indexed yet. "
                "Head to the 'Upload & Index' tab to add documents!"
            )
        else:
            st.write(f"Total documents: **{len(docs)}**")

            for d in docs:
                with st.expander(
                    f"📄 {d['filename']} "
                    f"({d['file_type'].upper()}) - "
                    f"{d['file_size_formatted']}"
                ):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown(f"**Doc ID:** `{d['doc_id']}`")
                        st.markdown(f"**File Type:** {d['file_type']}")
                        st.markdown(f"**Word Count:** {d['word_count']}")
                        st.markdown(f"**Upload Date:** {d['upload_date']}")

                    with col2:
                        st.markdown(
                            f"**Checksum:** `{d['checksum'][:16]}...`"
                        )
                        st.markdown(
                            f"**Keywords:** "
                            f"{', '.join(d.get('keywords', []))}"
                        )

                    from utils.file_manager import FileManager

                    text = FileManager.read_extracted_text(
                        d["doc_id"]
                    ) or ""

                    st.text_area(
                        "Extracted Content Preview",
                        text[:1000],
                        height=120,
                        key=f"lib_{d['doc_id']}"
                    )

                    if st.button(
                        "🗑️ Delete Document",
                        key=f"del_{d['doc_id']}"
                    ):
                        from indexing import IndexManager

                        IndexManager().delete_document(d["doc_id"])
                        db.delete_document(d["doc_id"])
                        FileManager.delete_document_files(
                            d["doc_id"],
                            d["stored_path"]
                        )

                        st.success(f"Deleted {d['filename']}!")
                        st.rerun()

    elif page == "📊 System Analytics":
        st.header("📊 OmniSearch AI System Analytics")

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Documents", stats["total_documents"])
        col2.metric("Total Words", f"{stats['total_words']:,}")
        col3.metric("Index Storage", stats["total_size_formatted"])
        col4.metric("Queries Executed", stats["total_searches"])

        st.markdown("### Document Distribution by Type")

        if stats["type_breakdown"]:
            for ftype, count in stats["type_breakdown"].items():
                st.write(f"- **{ftype.upper()}**: {count} file(s)")
        else:
            st.write("No files ingested yet.")


def run_cli():
    """Run the interactive terminal search interface."""
    print("=" * 60)
    print("OmniSearch AI - Interactive Terminal Interface")
    print("=" * 60)

    from database.database import Database
    from search import SearchEngine
    from retrieval import ResultRetriever

    db = Database()
    stats = db.get_stats()

    print(f"Total Indexed Documents: {stats['total_documents']}")
    print(f"Total Words: {stats['total_words']:,}")
    print(f"Storage Used: {stats['total_size_formatted']}")
    print("-" * 60)
    print("To launch the Streamlit Web UI, run:")
    print("    python3 -m streamlit run app.py")
    print("=" * 60)

    se = SearchEngine()
    rr = ResultRetriever()

    # Use arguments after the script name as the search query.
    query_args = sys.argv[1:]

    if query_args and query_args[0] == "--scan":
        print("Use --scan only with the directory scanning command.")
        return

    if query_args:
        query = " ".join(query_args)
        print(f"\nSearching for: '{query}'")

        res = se.search(query, mode="hybrid")
        results = rr.retrieve_results(res)

        print(f"Found {len(results)} match(es):\n")

        for i, r in enumerate(results, 1):
            print(
                f"[{i}] {r['filename']} "
                f"({r['file_type'].upper()}) - "
                f"Score: {r['score']}"
            )
            print(f"    Snippet: {r['snippet']}")
            print(f"    Keywords: {', '.join(r['keywords'][:5])}\n")


def run_scan(folder_path: str):
    """Scan a local folder and ingest supported files."""
    from pipeline import IngestionPipeline
    from utils.directory_scanner import scan_directory_summary
    from utils.file_manager import FileManager

    folder = os.path.expanduser(folder_path)

    if not os.path.isdir(folder):
        print(f"Error: '{folder}' is not a valid directory.")
        sys.exit(1)

    print("=" * 60)
    print("⚡ OmniSearch AI - Local Directory Scanner")
    print("=" * 60)
    print(f"📂 Scanning: {folder}\n")

    # Phase 1: Discover supported files.
    summary = scan_directory_summary(folder)

    print(
        f"Found {summary['total_files']} supported files "
        f"({FileManager.format_file_size(summary['total_size_bytes'])})"
    )

    if summary["by_category"]:
        for cat, count in sorted(summary["by_category"].items()):
            print(f"  • {cat.upper()}: {count} file(s)")

    print()

    if summary["total_files"] == 0:
        print("No supported files found in this directory.")
        return

    # Phase 2: Ingest files.
    print("Starting ingestion pipeline...")
    print("-" * 60)

    pipeline = IngestionPipeline()
    result = pipeline.scan_and_ingest(folder)

    # Phase 3: Print summary.
    print("\n" + "=" * 60)
    print("📊 Scan & Ingest Summary")
    print("=" * 60)
    print(f"  Total Files Found:      {result['total_found']}")
    print(f"  Successfully Ingested:  {result['ingested']}")
    print(f"  Skipped (Duplicates):   {result['skipped_duplicate']}")
    print(f"  Failed:                 {result['failed']}")
    print("=" * 60)

    for t in result["traces"]:
        status = t.get(
            "status",
            "ingested" if t.get("success") else "failed"
        )

        if status == "ingested" or t.get("success"):
            icon = "✅"
        elif status == "skipped_duplicate":
            icon = "⏭️"
        else:
            icon = "❌"

        print(f"  {icon} {t['filename']} — {status}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--scan":
        # Directory scan mode.
        if len(sys.argv) < 3:
            print("Usage: python app.py --scan /path/to/folder")
            sys.exit(1)

        run_scan(sys.argv[2])

    elif len(sys.argv) > 1:
        # CLI search mode.
        run_cli()

    elif HAS_STREAMLIT:
        # Running app.py directly without arguments prints instructions.
        print("To start the web app, run:")
        print("    python -m streamlit run app.py")

    else:
        print("Streamlit is not installed.")
        print("Install dependencies using:")
        print("    python3 -m pip install -r requirements.txt")
