from typing import List, Tuple, Optional
from indexing import IndexManager
from utils.logger import setup_logger

logger = setup_logger("SimilaritySearch")

class SimilaritySearch:
    """Executes FAISS / vector cosine similarity semantic search."""

    def __init__(self, index_manager: Optional[IndexManager] = None):
        self.index_manager = index_manager or IndexManager()

    def search(
        self,
        query: str,
        top_k: int = 20
    ) -> List[Tuple[str, float]]:
        """
        Executes semantic vector similarity search.
        Returns list of (doc_id, score) where score is in [-1, 1] range (normalized to [0, 1]).
        """
        if not query.strip():
            return []

        raw_results = self.index_manager.vector_index.search(
            query=query,
            top_k=top_k
        )

        # Normalize cosine similarity from [-1, 1] to [0, 1]
        normalized = []
        for doc_id, score in raw_results:
            norm_score = max(0.0, min(1.0, (score + 1.0) / 2.0))
            normalized.append((doc_id, norm_score))

        return normalized
