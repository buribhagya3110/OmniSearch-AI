import os
from pathlib import Path
from typing import List
from pipeline import IngestionPipeline
from utils.logger import setup_logger

logger = setup_logger("UploadPage")

def render_upload_page(st):
    """Renders document upload and indexing interface matching the flowchart pipeline."""
    st.header("📤 Document Ingestion Pipeline")
    st.markdown(
        "Upload files to trigger the full ingestion pipeline: "
        "`File Detection` ➔ `Dedicated Parser` ➔ `Cleaning & NLP` ➔ `Metadata Extraction` ➔ `Dual Indexing` ➔ `SQLite Storage`."
    )

    pipeline = IngestionPipeline()

    uploaded_files = st.file_uploader(
        "Supported formats: PDF, DOCX, PPTX, Images (PNG, JPG, TIFF), Audio (MP3, WAV), Video (MP4), Source Code (Python, JS, Java, C++, HTML, SQL, etc.)",
        type=[
            "pdf", "docx", "doc", "pptx", "ppt", "png", "jpg", "jpeg", "tiff", "bmp", "webp",
            "mp3", "wav", "m4a", "flac", "ogg", "mp4", "mkv", "mov", "avi",
            "py", "js", "ts", "java", "c", "cpp", "go", "rs", "html", "css", "sql", "json", "yaml", "md", "txt"
        ],
        accept_multiple_files=True
    )

    if uploaded_files:
        st.write(f"Selected **{len(uploaded_files)}** file(s) for ingestion.")
        if st.button("🚀 Ingest & Index All Documents", type="primary"):
            progress_bar = st.progress(0)
            status_box = st.empty()

            success_count = 0
            for i, file in enumerate(uploaded_files):
                filename = file.name
                file_bytes = file.read()

                status_box.info(f"Ingesting ({i+1}/{len(uploaded_files)}): **{filename}**...")

                trace = pipeline.process_file(file_bytes, filename)

                if trace.get("success"):
                    success_count += 1
                    stages = trace.get("stages", {})
                    det = stages.get("2_file_type_detection", {})
                    pars = stages.get("3_parser", {})
                    meta = stages.get("5_metadata_extraction", {})

                    with st.expander(f"✅ Ingested: **{filename}** ({det.get('category', '').upper()}) in {trace.get('elapsed_ms')}ms"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("**1. File Type Detection:**")
                            st.write(f"- Category: `{det.get('category')}`")
                            st.write(f"- MIME: `{det.get('mime_type')}`")
                            st.write(f"- Extension: `{det.get('extension')}`")

                            st.markdown("**2. Parser Module:**")
                            st.write(f"- Parser: `{pars.get('parser_used')}`")
                            st.write(f"- Extracted Characters: `{pars.get('raw_text_length')}`")

                        with col2:
                            st.markdown("**3. Text Cleaning & NLP:**")
                            cln = stages.get("4_text_extraction_cleaning", {})
                            st.write(f"- Tokens: `{cln.get('token_count')}` | Stemmed: `{cln.get('stemmed_token_count')}`")

                            st.markdown("**4. Indexing & Storage:**")
                            idx = stages.get("6_indexing_engine", {})
                            st.write(f"- Whoosh BM25 Indexed: `{idx.get('whoosh_bm25_indexed')}`")
                            st.write(f"- FAISS Vector ID: `{idx.get('faiss_vector_index_id')}`")
                            st.write(f"- SQLite DB: `Stored`")

                        st.markdown(f"**Keywords Extracted:** {', '.join(meta.get('keywords', []))}")
                else:
                    st.error(f"❌ Failed to process **{filename}**: {trace.get('error')}")

                progress_bar.progress((i + 1) / len(uploaded_files))

            status_box.empty()
            st.success(f"🎉 Pipeline Complete! Ingested **{success_count} / {len(uploaded_files)}** files successfully.")

    # ── Local Folder Scanner ──
    st.markdown("---")
    st.subheader("📂 Scan Local Folder")
    st.markdown(
        "Enter a folder path on your Mac to automatically discover and index all supported files. "
        "Hidden folders, system files, `node_modules`, `__pycache__`, etc. are skipped automatically."
    )

    folder_path = st.text_input(
        "Folder path",
        placeholder="e.g. ~/Documents/Lectures or /Users/you/Desktop/Project",
        key="scan_folder_path"
    )

    col_preview, col_scan = st.columns(2)

    with col_preview:
        if st.button("🔍 Preview Folder", disabled=not folder_path):
            import os
            expanded = os.path.expanduser(folder_path)
            if not os.path.isdir(expanded):
                st.error(f"'{expanded}' is not a valid directory.")
            else:
                from utils.directory_scanner import scan_directory_summary
                from utils.file_manager import FileManager
                with st.spinner("Scanning directory..."):
                    summary = scan_directory_summary(expanded)
                st.info(
                    f"Found **{summary['total_files']}** supported files "
                    f"({FileManager.format_file_size(summary['total_size_bytes'])})"
                )
                if summary["by_category"]:
                    for cat, count in sorted(summary["by_category"].items()):
                        st.write(f"  • **{cat.upper()}**: {count} file(s)")
                if summary["files"]:
                    with st.expander(f"📋 File list (first 50 of {summary['total_files']})"):
                        for f in summary["files"][:50]:
                            st.write(f"  • `{f['filename']}` ({f['category']})")

    with col_scan:
        if st.button("⚡ Scan & Index All", type="primary", disabled=not folder_path):
            import os
            expanded = os.path.expanduser(folder_path)
            if not os.path.isdir(expanded):
                st.error(f"'{expanded}' is not a valid directory.")
            else:
                scan_status = st.empty()
                scan_status.info(f"Scanning and ingesting files from `{expanded}`...")
                result = pipeline.scan_and_ingest(expanded)
                scan_status.empty()

                st.success(
                    f"🎉 Scan Complete! "
                    f"**{result['ingested']}** ingested, "
                    f"**{result['skipped_duplicate']}** duplicates skipped, "
                    f"**{result['failed']}** failed "
                    f"(out of {result['total_found']} files found)."
                )

                for t in result["traces"]:
                    status = t.get("status", "ingested" if t.get("success") else "failed")
                    if status == "skipped_duplicate":
                        st.write(f"  ⏭️ `{t['filename']}` — duplicate")
                    elif t.get("success"):
                        st.write(f"  ✅ `{t['filename']}` — {t.get('elapsed_ms', '')}ms")
                    else:
                        st.write(f"  ❌ `{t['filename']}` — {t.get('error', 'failed')}")
