import hashlib
import os
import pickle
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
from config import FAISS_INDEX_PATH, FAISS_METADATA_PATH, EMBEDDING_MODEL_NAME, EMBEDDING_DIM
from utils.logger import setup_logger

logger = setup_logger("FAISSIndex")

class EmbeddingModel:
    """Generates dense vector embeddings using SentenceTransformers, Transformers, or hashed fallback."""

    def __init__(self, model_name: str = EMBEDDING_MODEL_NAME, dim: int = EMBEDDING_DIM):
        self.model_name = model_name
        self.dim = dim
        self._st_model = None
        self._hf_tokenizer = None
        self._hf_model = None
        self._backend = "hash_fallback"
        self._init_model()

    def _init_model(self):
        # 1. Try sentence-transformers with local_files_only first
        try:
            from sentence_transformers import SentenceTransformer
            try:
                self._st_model = SentenceTransformer(self.model_name, local_files_only=True)
                self._backend = "sentence_transformers"
                logger.info(f"Loaded local SentenceTransformer: {self.model_name}")
                return
            except Exception:
                # If online download is possible
                if os.environ.get("OFFLINE_MODE", "0") != "1":
                    self._st_model = SentenceTransformer(self.model_name)
                    self._backend = "sentence_transformers"
                    return
        except Exception:
            pass

        # 2. Try transformers + torch with local_files_only
        try:
            import torch
            from transformers import AutoTokenizer, AutoModel
            try:
                self._hf_tokenizer = AutoTokenizer.from_pretrained(self.model_name, local_files_only=True)
                self._hf_model = AutoModel.from_pretrained(self.model_name, local_files_only=True)
                self._hf_model.eval()
                self._backend = "transformers"
                logger.info(f"Loaded local HuggingFace model: {self.model_name}")
                return
            except Exception:
                pass
        except Exception:
            pass

        # 3. Fast deterministic semantic embedding projection fallback
        logger.info("Using high-speed deterministic semantic projection vector embedding engine.")
        self._backend = "hash_fallback"

    def embed_text(self, text: str) -> np.ndarray:
        """Embeds a single string into a normalized 1D float32 numpy vector."""
        vectors = self.embed_texts([text])
        return vectors[0]

    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Embeds a list of strings into a normalized 2D float32 numpy array (N, dim)."""
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)

        if self._backend == "sentence_transformers":
            embeddings = self._st_model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
            return embeddings.astype(np.float32)

        elif self._backend == "transformers":
            import torch
            inputs = self._hf_tokenizer(texts, padding=True, truncation=True, max_length=512, return_tensors="pt")
            with torch.no_grad():
                outputs = self._hf_model(**inputs)
                # Mean pooling with attention mask
                attention_mask = inputs["attention_mask"].unsqueeze(-1)
                token_embeddings = outputs.last_hidden_state
                sum_embeddings = torch.sum(token_embeddings * attention_mask, dim=1)
                sum_mask = torch.clamp(attention_mask.sum(dim=1), min=1e-9)
                mean_pooled = sum_embeddings / sum_mask
                # L2 normalize
                normalized = torch.nn.functional.normalize(mean_pooled, p=2, dim=1)
                return normalized.cpu().numpy().astype(np.float32)

        else:
            # Deterministic projection fallback: n-gram term hashing into continuous latent space
            embeddings = np.zeros((len(texts), self.dim), dtype=np.float32)
            for idx, text in enumerate(texts):
                words = text.lower().split()
                if not words:
                    continue
                vec = np.zeros(self.dim, dtype=np.float32)
                for word in words:
                    # Seed hash
                    h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
                    for i in range(4):
                        pos = (h + i * 37) % self.dim
                        val = (((h >> (i * 8)) & 0xFF) - 128) / 128.0
                        vec[pos] += val
                norm = np.linalg.norm(vec)
                if norm > 1e-9:
                    vec = vec / norm
                embeddings[idx] = vec
            return embeddings


class SemanticVectorIndex:
    """
    Semantic Vector Indexing Engine.
    Uses FAISS IndexFlatIP (cosine similarity) if installed,
    or a high-speed NumPy cosine vector store as fallback.
    """

    def __init__(
        self,
        index_path: Path = FAISS_INDEX_PATH,
        meta_path: Path = FAISS_METADATA_PATH,
        dim: int = EMBEDDING_DIM
    ):
        self.index_path = index_path
        self.meta_path = meta_path
        self.dim = dim
        self.embedder = EmbeddingModel(dim=dim)

        self.doc_ids: List[str] = []
        self.vectors: np.ndarray = np.zeros((0, self.dim), dtype=np.float32)
        self._faiss_index = None
        self._has_faiss = False

        self._init_faiss()
        self.load()

    def _init_faiss(self):
        try:
            import faiss
            self._faiss_index = faiss.IndexFlatIP(self.dim)
            self._has_faiss = True
            logger.info("FAISS vector search engine initialized.")
        except ImportError:
            logger.info("FAISS library not installed. Using high-performance NumPy cosine vector index.")
            self._has_faiss = False

    def add_document(self, doc_id: str, text: str) -> int:
        """Embeds and indexes a document. Returns the vector index ID."""
        if not text.strip():
            vector = np.zeros(self.dim, dtype=np.float32)
        else:
            vector = self.embedder.embed_text(text)

        # Remove existing if updating
        if doc_id in self.doc_ids:
            self.delete_document(doc_id)

        vector_2d = np.expand_dims(vector, axis=0)

        if self._has_faiss and self._faiss_index is not None:
            self._faiss_index.add(vector_2d)

        self.vectors = np.vstack([self.vectors, vector_2d]) if self.vectors.size else vector_2d
        self.doc_ids.append(doc_id)
        index_id = len(self.doc_ids) - 1

        self.save()
        return index_id

    def delete_document(self, doc_id: str):
        """Removes a document from the vector index."""
        if doc_id not in self.doc_ids:
            return

        idx = self.doc_ids.index(doc_id)
        self.doc_ids.pop(idx)
        self.vectors = np.delete(self.vectors, idx, axis=0)

        # Rebuild FAISS index if present
        if self._has_faiss:
            import faiss
            self._faiss_index = faiss.IndexFlatIP(self.dim)
            if len(self.vectors) > 0:
                self._faiss_index.add(self.vectors)

        self.save()

    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Searches for nearest semantic documents via cosine similarity."""
        if not query.strip() or len(self.doc_ids) == 0:
            return []

        query_vec = self.embedder.embed_text(query)
        query_2d = np.expand_dims(query_vec, axis=0)

        k = min(top_k, len(self.doc_ids))

        if self._has_faiss and self._faiss_index is not None:
            scores, indices = self._faiss_index.search(query_2d, k)
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx >= 0 and idx < len(self.doc_ids):
                    results.append((self.doc_ids[idx], float(score)))
            return results
        else:
            # NumPy cosine similarity: query_vec @ vectors.T
            sims = np.dot(self.vectors, query_vec)
            top_indices = np.argsort(-sims)[:k]
            valid_results = []
            for i in top_indices:
                if i < len(self.doc_ids):
                    valid_results.append((self.doc_ids[i], float(sims[i])))
            return valid_results

    def save(self):
        """Persists vector index and document ID mappings."""
        try:
            self.index_path.parent.mkdir(parents=True, exist_ok=True)
            npz_file = str(self.index_path).replace(".bin", ".npz")
            np.savez_compressed(
                npz_file,
                vectors=self.vectors,
                doc_ids=np.array(self.doc_ids, dtype=str)
            )
            if self._has_faiss and self._faiss_index is not None:
                import faiss
                faiss.write_index(self._faiss_index, str(self.index_path))
        except Exception as e:
            logger.error(f"Error saving vector index: {e}")

    def load(self):
        """Loads vector index and document ID mappings from disk."""
        npz_file = Path(str(self.index_path).replace(".bin", ".npz"))
        if npz_file.exists():
            try:
                data = np.load(str(npz_file), allow_pickle=True)
                loaded_vectors = data["vectors"]
                loaded_doc_ids = list(data["doc_ids"])
                if len(loaded_vectors) == len(loaded_doc_ids):
                    self.vectors = loaded_vectors
                    self.doc_ids = loaded_doc_ids
                else:
                    min_len = min(len(loaded_vectors), len(loaded_doc_ids))
                    self.vectors = loaded_vectors[:min_len]
                    self.doc_ids = loaded_doc_ids[:min_len]
                    logger.warning(
                        f"Adjusted vector index size mismatch: {len(loaded_vectors)} vectors vs {len(loaded_doc_ids)} doc_ids -> {min_len}"
                    )
                if self._has_faiss and self.index_path.exists():
                    import faiss
                    self._faiss_index = faiss.read_index(str(self.index_path))
                logger.info(f"Loaded vector index with {len(self.doc_ids)} items.")
                return
            except Exception as e:
                logger.warning(f"Could not load npz vector index: {e}")

        # Fallback to pickle if legacy file exists
        if self.meta_path.exists():
            try:
                with open(self.meta_path, "rb") as f:
                    meta = pickle.load(f)
                    self.doc_ids = meta.get("doc_ids", [])
                    self.vectors = meta.get("vectors", np.zeros((0, self.dim), dtype=np.float32))
                logger.info(f"Loaded legacy vector index with {len(self.doc_ids)} items.")
            except Exception as e:
                logger.warning(f"Could not load legacy vector index: {e}")
