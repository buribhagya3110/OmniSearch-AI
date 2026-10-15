import os
from pathlib import Path
from typing import Dict, Any, List

def render_result_card(st, item: Dict[str, Any], card_index: int):
    """Renders a styled search result card in Streamlit."""
    doc_id = item["doc_id"]
    filename = item["filename"]
    file_type = item["file_type"].upper()
    score = item["score"]
    match_type = item.get("match_type", "hybrid")
    score_pct = int(score * 100)
    stored_path = item.get("stored_path", "")
    full_text = item.get("full_text", "")
    similar_docs = item.get("similar_documents", [])
    keywords = item.get("keywords", [])

    # Card Container
    with st.container():
        # Header Row
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"### 📄 {filename}")
            # Badges
            type_color = {
                "PDF": "#ef4444",
                "DOCX": "#2563eb",
                "PPTX": "#ea580c",
                "IMAGE": "#8b5cf6",
                "AUDIO": "#06b6d4",
                "VIDEO": "#ec4899",
                "CODE": "#10b981"
            }.get(file_type, "#6b7280")

            badges_html = f"""
            <span style="background-color: {type_color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; margin-right: 6px;">{file_type}</span>
            <span style="background-color: #3b82f6; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; margin-right: 6px;">{match_type.upper()}</span>
            <span style="color: #64748b; font-size: 0.8rem; margin-right: 8px;">Size: {item.get('file_size_formatted', 'N/A')}</span>
            <span style="color: #64748b; font-size: 0.8rem;">Words: {item.get('word_count', 0)}</span>
            """
            st.markdown(badges_html, unsafe_allow_html=True)

        with col2:
            st.metric(label="Relevance Score", value=f"{score_pct}%", delta=f"{score:.2f}")

        # Highlighted Snippet
        st.markdown("**Matched Snippet:**")
        snippet_html = f"""
        <div style="background-color: #f8fafc; border-left: 4px solid #3b82f6; padding: 12px 16px; border-radius: 4px; font-size: 0.95rem; line-height: 1.6; color: #1e293b; margin: 8px 0;">
            {item.get('highlighted_snippet_html', item.get('snippet', ''))}
        </div>
        """
        st.markdown(snippet_html, unsafe_allow_html=True)

        # Audio / Video Timestamp & Player
        if file_type in ("AUDIO", "VIDEO"):
            if item.get("primary_timestamp"):
                st.markdown(f"⏱️ **Spoken Timestamp:** <span style='background-color: #06b6d4; color: white; padding: 2px 8px; border-radius: 10px; font-size: 0.8rem; font-weight: 600;'>{item['primary_timestamp']}</span>", unsafe_allow_html=True)
            if stored_path and os.path.exists(stored_path):
                st.audio(stored_path)
            
            audio_info = item.get("audio_info") or {}
            matched_segs = audio_info.get("matched_segments", [])
            if matched_segs:
                with st.expander("🎙️ Matching Spoken Segments & Timestamps"):
                    for seg in matched_segs:
                        st.markdown(f"• **`{seg['timestamp_range']}`**: {seg['text']}")

        # Keyword Chips
        if keywords:
            kw_html = " ".join([
                f'<span style="background-color: #e2e8f0; color: #334155; padding: 1px 7px; border-radius: 10px; font-size: 0.75rem; margin-right: 4px;">#{kw}</span>'
                for kw in keywords[:7]
            ])
            st.markdown(f"**Keywords:** {kw_html}", unsafe_allow_html=True)

        # Similar Documents
        if similar_docs:
            sim_chips = " | ".join([
                f"**{sd['filename']}** ({int(sd['similarity_score']*100)}%)"
                for sd in similar_docs
            ])
            st.markdown(f"🔗 *Similar Documents:* {sim_chips}")

        # Expandable Preview & Actions
        with st.expander("🔍 View Full Extracted Content"):
            st.text_area(label="Extracted Text Content", value=full_text[:4000], height=200, key=f"text_{doc_id}_{card_index}")
            if stored_path and os.path.exists(stored_path):
                try:
                    with open(stored_path, "rb") as f:
                        file_data = f.read()
                    st.download_button(
                        label=f"⬇️ Download Original ({Path(stored_path).name})",
                        data=file_data,
                        file_name=Path(stored_path).name,
                        key=f"dl_{doc_id}_{card_index}"
                    )
                except Exception:
                    pass

        st.markdown("<hr style='margin: 16px 0; border: 0; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)
