import math
import os
import pickle
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from config import WHOOSH_INDEX_DIR
from preprocessing import preprocess_text
from utils.logger import setup_logger

logger = setup_logger("WhooshIndex")

class PureBM25InvertedIndex:
    """
    Self-contained pure-Python BM25 inverted index.
    Provides identical BM25 keyword search capabilities, persistence,
    and field filtering without external C dependencies.
    """

    def __init__(self, index_dir: Path):
        self.index_dir = index_dir
        self.index_file = index_dir / "bm25_index.pkl"
        self.k1 = 1.5
        self.b = 0.75
        self.doc_len: Dict[str, int] = {}
        self.doc_meta: Dict[str, Dict[str, Any]] = {}
        self.inverted_index: Dict[str, Dict[str, int]] = {}  # term -> {doc_id: tf}
        self.avg_doc_len: float = 0.0
        self.total_docs: int = 0
        self.load()

    def add_document(self, doc_id: str, filename: str, file_type: str, content: str, keywords: List[str]):
        """Indexes or updates a document."""
        # Preprocess text into tokens
        res = preprocess_text(content, lowercase=True, remove_noise=True, remove_stopwords=True, stem=True)
        tokens = res.get("stemmed_tokens", [])

        # Also add keywords to tokens
        for kw in keywords:
            kw_res = preprocess_text(kw, lowercase=True, remove_stopwords=False, stem=True)
            tokens.extend(kw_res.get("stemmed_tokens", []))

        # Remove existing if updating
        if doc_id in self.doc_len:
            self.delete_document(doc_id)

        doc_length = len(tokens)
        self.doc_len[doc_id] = doc_length
        self.doc_meta[doc_id] = {
            "doc_id": doc_id,
            "filename": filename,
            "file_type": file_type,
            "keywords": keywords
        }

        # Update inverted index
        term_freqs: Dict[str, int] = {}
        for t in tokens:
            term_freqs[t] = term_freqs.get(t, 0) + 1

        for term, tf in term_freqs.items():
            if term not in self.inverted_index:
                self.inverted_index[term] = {}
            self.inverted_index[term][doc_id] = tf

        self.total_docs = len(self.doc_len)
        self.avg_doc_len = sum(self.doc_len.values()) / max(1, self.total_docs)
        self.save()

    def delete_document(self, doc_id: str):
        """Removes a document from the inverted index."""
        if doc_id in self.doc_len:
            del self.doc_len[doc_id]
        if doc_id in self.doc_meta:
            del self.doc_meta[doc_id]

        empty_terms = []
        for term, posting in self.inverted_index.items():
            if doc_id in posting:
                del posting[doc_id]
            if not posting:
                empty_terms.append(term)

        for term in empty_terms:
            del self.inverted_index[term]

        self.total_docs = len(self.doc_len)
        self.avg_doc_len = (sum(self.doc_len.values()) / self.total_docs) if self.total_docs > 0 else 0.0
        self.save()

    def search(self, query: str, category: Optional[str] = None, limit: int = 10) -> List[Tuple[str, float]]:
        """Computes BM25 ranking scores for matching documents."""
        if not query or self.total_docs == 0:
            return []

        res = preprocess_text(query, lowercase=True, remove_noise=True, remove_stopwords=True, stem=True)
        query_terms = res.get("stemmed_tokens", [])
        if not query_terms:
            return []

        scores: Dict[str, float] = {}

        for term in query_terms:
            if term not in self.inverted_index:
                continue

            posting = self.inverted_index[term]
            df = len(posting)
            # Standard Lucene/Okapi BM25 IDF formula
            idf = math.log(1.0 + (self.total_docs - df + 0.5) / (df + 0.5))

            for doc_id, tf in posting.items():
                # Apply category filter
                if category and category != "all":
                    if self.doc_meta.get(doc_id, {}).get("file_type") != category:
                        continue

                dl = self.doc_len.get(doc_id, self.avg_doc_len)
                num = tf * (self.k1 + 1.0)
                denom = tf + self.k1 * (1.0 - self.b + self.b * (dl / max(1.0, self.avg_doc_len)))
                bm25 = idf * (num / denom)
                scores[doc_id] = scores.get(doc_id, 0.0) + bm25

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked[:limit]

    def save(self):
        """Persists the index to disk."""
        self.index_dir.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.index_file, "wb") as f:
                pickle.dump({
                    "doc_len": self.doc_len,
                    "doc_meta": self.doc_meta,
                    "inverted_index": self.inverted_index,
                    "avg_doc_len": self.avg_doc_len,
                    "total_docs": self.total_docs
                }, f)
        except Exception as e:
            logger.error(f"Failed to persist BM25 index: {e}")

    def load(self):
        """Loads index from disk if present."""
        if self.index_file.exists():
            try:
                with open(self.index_file, "rb") as f:
                    data = pickle.load(f)
                    self.doc_len = data.get("doc_len", {})
                    self.doc_meta = data.get("doc_meta", {})
                    self.inverted_index = data.get("inverted_index", {})
                    self.avg_doc_len = data.get("avg_doc_len", 0.0)
                    self.total_docs = data.get("total_docs", 0)
                logger.info(f"Loaded BM25 index with {self.total_docs} documents.")
            except Exception as e:
                logger.warning(f"Could not load BM25 index: {e}")


class KeywordIndex:
    """
    Keyword Indexing Engine.
    Uses Whoosh if installed, else seamlessly falls back to PureBM25InvertedIndex.
    """

    def __init__(self, index_dir: Path = WHOOSH_INDEX_DIR):
        self.index_dir = index_dir
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._whoosh_available = False
        self._index = None

        try:
            from whoosh import index
            from whoosh.fields import Schema, ID, TEXT, KEYWORD
            from whoosh.analysis import StandardAnalyzer

            schema = Schema(
                doc_id=ID(stored=True, unique=True),
                filename=TEXT(stored=True),
                file_type=KEYWORD(stored=True),
                content=TEXT(stored=False, analyzer=StandardAnalyzer()),
                keywords=KEYWORD(stored=True)
            )

            if index.exists_in(str(self.index_dir)):
                self._index = index.open_dir(str(self.index_dir))
            else:
                self._index = index.create_in(str(self.index_dir), schema)

            self._whoosh_available = True
            logger.info("Whoosh search engine initialized successfully.")
        except ImportError:
            logger.info("Whoosh not installed. Initializing built-in BM25 inverted index engine.")
            self._index = PureBM25InvertedIndex(self.index_dir)
        except Exception as e:
            logger.warning(f"Whoosh error: {e}. Falling back to built-in BM25 engine.")
            self._index = PureBM25InvertedIndex(self.index_dir)

    def add_document(self, doc_id: str, filename: str, file_type: str, content: str, keywords: List[str]):
        """Indexes a document in the keyword index."""
        if self._whoosh_available:
            from whoosh.writing import AsyncWriter
            writer = AsyncWriter(self._index)
            writer.update_document(
                doc_id=doc_id,
                filename=filename,
                file_type=file_type,
                content=content,
                keywords=" ".join(keywords)
            )
            writer.commit()
        else:
            self._index.add_document(doc_id, filename, file_type, content, keywords)

    def delete_document(self, doc_id: str):
        """Removes a document from the keyword index."""
        if self._whoosh_available:
            from whoosh.writing import AsyncWriter
            writer = AsyncWriter(self._index)
            writer.delete_by_term("doc_id", doc_id)
            writer.commit()
        else:
            self._index.delete_document(doc_id)

    def search(self, query_str: str, category: Optional[str] = None, limit: int = 10) -> List[Tuple[str, float]]:
        """Executes BM25 keyword query."""
        if self._whoosh_available:
            from whoosh.qparser import MultifieldParser, OrGroup
            with self._index.searcher() as searcher:
                parser = MultifieldParser(["content", "filename", "keywords"], schema=self._index.schema, group=OrGroup)
                query = parser.parse(query_str)
                
                filter_query = None
                if category and category != "all":
                    from whoosh.query import Term
                    filter_query = Term("file_type", category)

                results = searcher.search(query, filter=filter_query, limit=limit)
                return [(r["doc_id"], float(r.score)) for r in results]
        else:
            return self._index.search(query_str, category=category, limit=limit)
