from typing import Dict, Any, List, Optional
from .whoosh_index import KeywordIndex
from .faiss_index import SemanticVectorIndex
from utils.logger import setup_logger

logger = setup_logger("IndexManager")

class IndexManager:
    """Unified manager coordinating both Keyword (Whoosh/BM25) and Semantic (FAISS) indexing."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(IndexManager, cls).__new__(cls)
            cls._instance.keyword_index = KeywordIndex()
            cls._instance.vector_index = SemanticVectorIndex()
        return cls._instance

    def index_document(
        self,
        doc_id: str,
        filename: str,
        file_type: str,
        content: str,
        keywords: List[str]
    ) -> int:
        """Indexes a document in both keyword and semantic indices."""
        logger.info(f"Indexing document '{filename}' ({doc_id}) into Keyword and Vector indices...")

        # 1. Keyword indexing
        self.keyword_index.add_document(
            doc_id=doc_id,
            filename=filename,
            file_type=file_type,
            content=content,
            keywords=keywords
        )

        # 2. Semantic vector indexing
        # Combine filename, keywords, and document content for rich contextual vector representation
        embedding_text = f"Title: {filename}\nType: {file_type}\nKeywords: {', '.join(keywords)}\n\n{content[:4000]}"
        faiss_id = self.vector_index.add_document(doc_id, embedding_text)

        return faiss_id

    def delete_document(self, doc_id: str):
        """Removes a document from both indices."""
        self.keyword_index.delete_document(doc_id)
        self.vector_index.delete_document(doc_id)
        logger.info(f"Removed document {doc_id} from all indices.")

    def reindex_all(self):
        """Re-indexes all existing documents from the SQLite database."""
        from database.database import Database
        from utils.file_manager import FileManager
        db = Database()
        docs = db.list_all_documents(limit=1000)
        logger.info(f"Re-indexing {len(docs)} documents from database...")
        for d in docs:
            doc_id = d["doc_id"]
            text = FileManager.read_extracted_text(doc_id) or ""
            keywords = d.get("keywords", [])
            faiss_id = self.index_document(
                doc_id=doc_id,
                filename=d["filename"],
                file_type=d["file_type"],
                content=text,
                keywords=keywords
            )
            db.update_index_reference(doc_id, faiss_id)
        logger.info(f"Re-indexing complete for {len(docs)} documents.")

__all__ = ["KeywordIndex", "SemanticVectorIndex", "IndexManager"]
