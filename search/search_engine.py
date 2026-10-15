import re
from typing import Dict, Any, List, Optional
from config import DEFAULT_TOP_K, BM25_WEIGHT, SEMANTIC_WEIGHT, EXACT_MATCH_BOOST
from database.database import Database
from utils.file_manager import FileManager
from utils.logger import setup_logger
from .query_processor import QueryProcessor
from .bm25_ranker import BM25Ranker
from .similarity import SimilaritySearch

logger = setup_logger("SearchEngine")

class SearchEngine:
    """
    Search & Ranking Engine executing BM25, FAISS Semantic Similarity,
    Exact Match, and Hybrid RRF / Blended Search.
    """

    def __init__(self):
        self.db = Database()
        self.bm25 = BM25Ranker()
        self.similarity = SimilaritySearch()
        self.query_processor = QueryProcessor()
        self._sync_vocabulary()

    def _sync_vocabulary(self):
        """Builds query processor spell-check vocabulary from database keywords."""
        try:
            stats = self.db.get_stats()
            docs = self.db.list_all_documents(limit=500)
            words = []
            for d in docs:
                words.extend(d.get("keywords", []))
                words.append(d.get("filename", ""))
            self.query_processor.update_vocabulary(words)
        except Exception as e:
            logger.warning(f"Failed to sync search vocabulary: {e}")

    def _exact_match_search(self, query: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Checks for exact substring occurrences in document contents and filenames."""
        clean_q = query.lower().strip()
        if not clean_q:
            return []

        docs = self.db.list_all_documents(category=category, limit=500)
        matches = []
        for doc in docs:
            doc_id = doc["doc_id"]
            filename = doc.get("filename", "").lower()
            text = FileManager.read_extracted_text(doc_id) or ""
            text_lower = text.lower()

            count_in_text = text_lower.count(clean_q)
            in_filename = clean_q in filename

            # Check if all tokens appear exactly in text
            words = [w for w in clean_q.split() if len(w) > 1]
            all_words_present = all(w in text_lower or w in filename for w in words) if len(words) > 1 else False

            if count_in_text > 0 or in_filename:
                # Score based on frequency and title bonus
                score = min(1.0, 0.5 + (count_in_text * 0.1) + (0.4 if in_filename else 0.0))
                matches.append({
                    "doc_id": doc_id,
                    "score": score,
                    "match_type": "exact",
                    "exact_occurrences": count_in_text
                })
            elif all_words_present:
                score = min(0.9, 0.35 + (0.1 * len(words)))
                matches.append({
                    "doc_id": doc_id,
                    "score": score,
                    "match_type": "exact (all terms)",
                    "exact_occurrences": sum(text_lower.count(w) for w in words)
                })

        return sorted(matches, key=lambda x: x["score"], reverse=True)

    def search(
        self,
        query: str,
        mode: str = "hybrid",
        category: Optional[str] = None,
        top_k: int = DEFAULT_TOP_K,
        bm25_weight: float = BM25_WEIGHT,
        semantic_weight: float = SEMANTIC_WEIGHT,
        min_score: float = 0.0
    ) -> Dict[str, Any]:
        """
        Executes query across specified search mode:
        'hybrid', 'semantic', 'keyword', or 'exact'.
        Returns structured search results and query metadata.
        """
        # Process query
        processed_query = self.query_processor.process(query)
        clean_text = processed_query.get("clean_query") or query

        results_by_doc: Dict[str, Dict[str, Any]] = {}

        if mode == "exact":
            exact_matches = self._exact_match_search(query, category=category)
            for item in exact_matches:
                doc_id = item["doc_id"]
                results_by_doc[doc_id] = {
                    "doc_id": doc_id,
                    "score": item["score"],
                    "bm25_score": 0.0,
                    "semantic_score": 0.0,
                    "match_type": "exact"
                }

        elif mode == "keyword":
            bm25_hits = self.bm25.search(clean_text, category=category, limit=top_k * 2)
            for doc_id, score in bm25_hits:
                results_by_doc[doc_id] = {
                    "doc_id": doc_id,
                    "score": score,
                    "bm25_score": score,
                    "semantic_score": 0.0,
                    "match_type": "keyword"
                }

        elif mode == "semantic":
            sem_hits = self.similarity.search(clean_text, top_k=top_k * 2)
            for doc_id, score in sem_hits:
                # Apply category filter if requested
                if category and category != "all":
                    doc = self.db.get_document(doc_id)
                    if not doc or doc.get("file_type") != category:
                        continue
                results_by_doc[doc_id] = {
                    "doc_id": doc_id,
                    "score": score,
                    "bm25_score": 0.0,
                    "semantic_score": score,
                    "match_type": "semantic"
                }

        else:  # Hybrid Mode (BM25 + Semantic FAISS + Exact Match Boost)
            bm25_hits = dict(self.bm25.search(clean_text, category=category, limit=top_k * 2))
            sem_hits_raw = self.similarity.search(clean_text, top_k=top_k * 2)

            sem_hits = {}
            for doc_id, score in sem_hits_raw:
                if category and category != "all":
                    doc = self.db.get_document(doc_id)
                    if not doc or doc.get("file_type") != category:
                        continue
                sem_hits[doc_id] = score

            all_doc_ids = set(bm25_hits.keys()).union(set(sem_hits.keys()))

            for doc_id in all_doc_ids:
                b_score = bm25_hits.get(doc_id, 0.0)
                s_score = sem_hits.get(doc_id, 0.0)

                # Weighted linear combination
                combined = (bm25_weight * b_score) + (semantic_weight * s_score)

                # Check for exact matches to boost
                text = FileManager.read_extracted_text(doc_id) or ""
                exact_boost = 0.0
                if query.lower() in text.lower():
                    exact_boost = 0.15

                total_score = min(1.0, combined + exact_boost)

                match_type = "hybrid"
                if b_score > 0 and s_score > 0:
                    match_type = "hybrid (keyword + semantic)"
                elif b_score > 0:
                    match_type = "keyword"
                elif s_score > 0:
                    match_type = "semantic"

                results_by_doc[doc_id] = {
                    "doc_id": doc_id,
                    "score": total_score,
                    "bm25_score": b_score,
                    "semantic_score": s_score,
                    "match_type": match_type
                }

        # Filter by minimum score and sort
        final_list = [
            item for item in results_by_doc.values()
            if item["score"] >= min_score
        ]
        final_list.sort(key=lambda x: x["score"], reverse=True)
        final_results = final_list[:top_k]

        # Log search query
        self.db.log_search(query, mode, len(final_results))

        return {
            "query": query,
            "processed_query": processed_query,
            "mode": mode,
            "total_matches": len(final_results),
            "results": final_results
        }
