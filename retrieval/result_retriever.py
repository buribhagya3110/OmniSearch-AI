from typing import Dict, Any, List, Optional
from database.database import Database
from indexing import IndexManager
from utils.file_manager import FileManager
from utils.logger import setup_logger
from .snippet_generator import SnippetGenerator
from .highlighter import Highlighter

logger = setup_logger("ResultRetriever")

class ResultRetriever:
    """
    Enriches raw search hits with metadata, contextual snippets,
    highlighted keywords, and similar document recommendations.
    """

    def __init__(self):
        self.db = Database()
        self.index_manager = IndexManager()

    def get_similar_documents(self, doc_id: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Finds related/similar documents using vector semantic similarity."""
        try:
            doc_text = FileManager.read_extracted_text(doc_id) or ""
            if not doc_text:
                return []

            # Query vector index with document summary
            sample_query = doc_text[:1000]
            hits = self.index_manager.vector_index.search(sample_query, top_k=limit + 1)

            similar = []
            for hit_id, score in hits:
                if hit_id != doc_id:
                    doc_meta = self.db.get_document(hit_id)
                    if doc_meta:
                        similar.append({
                            "doc_id": hit_id,
                            "filename": doc_meta.get("filename"),
                            "file_type": doc_meta.get("file_type"),
                            "similarity_score": round(score, 3)
                        })
                if len(similar) >= limit:
                    break

            return similar
        except Exception as e:
            logger.warning(f"Error finding similar documents for {doc_id}: {e}")
            return []

    def retrieve_results(
        self,
        search_output: Dict[str, Any],
        fetch_similar: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Enriches list of raw search hits into full retrieval cards.
        """
        query = search_output.get("query", "")
        raw_results = search_output.get("results", [])
        enriched_results = []

        for hit in raw_results:
            doc_id = hit["doc_id"]
            doc_meta = self.db.get_document(doc_id)
            if not doc_meta:
                continue

            # Fetch full text
            full_text = FileManager.read_extracted_text(doc_id) or ""

            # Generate context-aware snippet
            raw_snippet = SnippetGenerator.generate_snippet(full_text, query)

            # Highlight keywords
            highlighted_snippet = Highlighter.highlight_html(raw_snippet, query)
            markdown_snippet = Highlighter.highlight_markdown(raw_snippet, query)

            # Similar documents
            similar_docs = self.get_similar_documents(doc_id, limit=3) if fetch_similar else []

            # Audio/Video Timestamp & Segment Matching
            audio_info = None
            primary_timestamp = None
            matched_segments = []

            if doc_meta.get("file_type") in ("audio", "video"):
                parser_meta = doc_meta.get("parser_metadata", {})
                duration_formatted = parser_meta.get("duration_formatted", "")

                # Extract query tokens for segment matching
                query_tokens = [t.lower() for t in query.split() if len(t) > 1]
                segments = doc_meta.get("audio_segments") or parser_meta.get("segments", [])

                for s in segments:
                    seg_text = s.get("text", "")
                    st_val = float(s.get("start_time", s.get("start", 0.0)))
                    en_val = float(s.get("end_time", s.get("end", st_val)))
                    st_str = s.get("start_formatted") or f"{int(st_val)//60:02d}:{int(st_val)%60:02d}"
                    en_str = s.get("end_formatted") or f"{int(en_val)//60:02d}:{int(en_val)%60:02d}"
                    time_range = f"{st_str} - {en_str}"

                    # Check if query words appear in this segment
                    hits = sum(1 for q_term in query_tokens if q_term in seg_text.lower())
                    if hits > 0 or not query_tokens:
                        matched_segments.append({
                            "start": st_val,
                            "end": en_val,
                            "timestamp_range": time_range,
                            "text": seg_text,
                            "highlighted_html": Highlighter.highlight_html(seg_text, query),
                            "hits": hits
                        })

                if matched_segments:
                    matched_segments.sort(key=lambda x: x["hits"], reverse=True)
                    primary_timestamp = matched_segments[0]["timestamp_range"]
                    # If snippet generator didn't pick up the exact audio spoken line, use the matched segment
                    if matched_segments[0]["hits"] > 0:
                        best_seg = matched_segments[0]
                        raw_snippet = f"[{best_seg['timestamp_range']}] {best_seg['text']}"
                        highlighted_snippet = f"<span style='color: #38bdf8; font-weight: bold;'>[{best_seg['timestamp_range']}]</span> {best_seg['highlighted_html']}"

                audio_info = {
                    "duration_formatted": duration_formatted,
                    "primary_timestamp": primary_timestamp,
                    "matched_segments": matched_segments[:4],
                    "total_segments": len(segments)
                }

            enriched_results.append({
                "doc_id": doc_id,
                "filename": doc_meta.get("filename"),
                "stored_path": doc_meta.get("stored_path"),
                "file_type": doc_meta.get("file_type"),
                "extension": doc_meta.get("extension"),
                "file_size_formatted": doc_meta.get("file_size_formatted"),
                "upload_date": doc_meta.get("upload_date"),
                "word_count": doc_meta.get("word_count"),
                "keywords": doc_meta.get("keywords", []),
                "score": round(hit.get("score", 0.0), 3),
                "bm25_score": round(hit.get("bm25_score", 0.0), 3),
                "semantic_score": round(hit.get("semantic_score", 0.0), 3),
                "match_type": hit.get("match_type", "hybrid"),
                "snippet": raw_snippet,
                "highlighted_snippet_html": highlighted_snippet,
                "highlighted_snippet_md": markdown_snippet,
                "full_text": full_text,
                "similar_documents": similar_docs,
                "audio_info": audio_info,
                "primary_timestamp": primary_timestamp
            })

        return enriched_results

