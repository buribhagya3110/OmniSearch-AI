from typing import List, Tuple, Optional, Dict
from indexing import IndexManager
from utils.logger import setup_logger

logger = setup_logger("BM25Ranker")

class BM25Ranker:
    """Executes BM25 keyword searches and provides normalized ranking scores."""

    def __init__(self, index_manager: Optional[IndexManager] = None):
        self.index_manager = index_manager or IndexManager()

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 20
    ) -> List[Tuple[str, float]]:
        """
        Executes BM25 search.
        Returns list of (doc_id, score) sorted by score descending.
        """
        if not query.strip():
            return []

        raw_results = self.index_manager.keyword_index.search(
            query_str=query,
            category=category,
            limit=limit
        )

        if not raw_results:
            return []

        # Normalize BM25 scores to [0, 1] range using max score
        max_score = max(score for _, score in raw_results) if raw_results else 1.0
        normalized_results = []
        for doc_id, score in raw_results:
            norm_score = score / max_score if max_score > 0 else 0.0
            normalized_results.append((doc_id, norm_score))

        return normalized_results
