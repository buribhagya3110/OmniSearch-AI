import json
import sqlite3
import threading
from typing import Dict, Any, List, Optional
from config import DB_PATH
from database.schema import (
    CREATE_DOCUMENTS_TABLE, CREATE_KEYWORDS_TABLE,
    CREATE_AUDIO_SEGMENTS_TABLE, CREATE_SEARCH_HISTORY_TABLE, CREATE_INDEXES
)
from utils.file_manager import FileManager
from utils.logger import setup_logger

logger = setup_logger("Database")

class Database:
    """Thread-safe SQLite database manager for metadata and index references."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_path: str = str(DB_PATH)):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(Database, cls).__new__(cls)
                cls._instance.db_path = db_path
                cls._instance._init_db()
        return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self):
        """Initializes database tables, columns, and indexes with automatic migration."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(CREATE_DOCUMENTS_TABLE)
            cursor.execute(CREATE_KEYWORDS_TABLE)
            cursor.execute(CREATE_AUDIO_SEGMENTS_TABLE)
            cursor.execute(CREATE_SEARCH_HISTORY_TABLE)
            cursor.executescript(CREATE_INDEXES)

            # Schema migration: check if metadata_json column exists
            cursor.execute("PRAGMA table_info(documents)")
            cols = [col["name"] for col in cursor.fetchall()]
            if "metadata_json" not in cols:
                try:
                    cursor.execute("ALTER TABLE documents ADD COLUMN metadata_json TEXT")
                except Exception as e:
                    logger.debug(f"Column metadata_json migration notice: {e}")

            conn.commit()
        logger.info(f"Database initialized at {self.db_path}")


    def add_document(
        self,
        metadata: Dict[str, Any],
        extracted_text_path: str = "",
        faiss_index_id: Optional[int] = None
    ) -> bool:
        """Inserts a new document record, keywords, and any audio/video segment timestamps."""
        doc_id = metadata["doc_id"]
        parser_meta = metadata.get("parser_metadata", {})
        meta_json_str = json.dumps(parser_meta, default=str)

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO documents (
                        doc_id, filename, stored_path, file_type, extension,
                        mime_type, file_size, file_size_formatted, upload_date,
                        checksum, word_count, char_count, extracted_text_path,
                        faiss_index_id, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    doc_id,
                    metadata.get("filename", ""),
                    metadata.get("stored_path", ""),
                    metadata.get("file_type", "unknown"),
                    metadata.get("extension", ""),
                    metadata.get("mime_type", ""),
                    metadata.get("file_size", 0),
                    metadata.get("file_size_formatted", ""),
                    metadata.get("upload_date", ""),
                    metadata.get("checksum", ""),
                    metadata.get("word_count", 0),
                    metadata.get("char_count", 0),
                    extracted_text_path,
                    faiss_index_id,
                    meta_json_str
                ))

                # Insert keywords
                cursor.execute("DELETE FROM document_keywords WHERE doc_id = ?", (doc_id,))
                keywords = metadata.get("keywords", [])
                for kw in keywords:
                    cursor.execute(
                        "INSERT INTO document_keywords (doc_id, keyword) VALUES (?, ?)",
                        (doc_id, kw)
                    )

                # Insert audio/video segments if present
                cursor.execute("DELETE FROM audio_segments WHERE doc_id = ?", (doc_id,))
                segments = parser_meta.get("segments", [])
                for idx, seg in enumerate(segments):
                    cursor.execute("""
                        INSERT INTO audio_segments (doc_id, segment_index, start_time, end_time, text)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        doc_id,
                        idx,
                        float(seg.get("start", 0.0)),
                        float(seg.get("end", 0.0)),
                        seg.get("text", "").strip()
                    ))

                conn.commit()
            logger.info(f"Document {doc_id} ('{metadata.get('filename')}') saved to database.")
            return True
        except Exception as e:
            logger.error(f"Failed to add document {doc_id}: {e}")
            return False

    def update_index_reference(self, doc_id: str, faiss_index_id: int):
        """Updates the FAISS index vector offset reference for a document."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE documents SET faiss_index_id = ? WHERE doc_id = ?",
                (faiss_index_id, doc_id)
            )
            conn.commit()

    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        if seconds is None:
            return "00:00"
        total_sec = max(0, int(seconds))
        hours = total_sec // 3600
        mins = (total_sec % 3600) // 60
        secs = total_sec % 60
        if hours > 0:
            return f"{hours:02d}:{mins:02d}:{secs:02d}"
        return f"{mins:02d}:{secs:02d}"

    def get_audio_segments(self, doc_id: str) -> List[Dict[str, Any]]:
        """Retrieves all timestamped audio segments for a document."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT segment_index, start_time, end_time, text FROM audio_segments WHERE doc_id = ? ORDER BY segment_index ASC",
                (doc_id,)
            )
            rows = cursor.fetchall()
            results = []
            for r in rows:
                d = dict(r)
                st = d.get("start_time", 0.0)
                et = d.get("end_time", st)
                st_fmt = self._format_timestamp(st)
                et_fmt = self._format_timestamp(et)
                d["start_formatted"] = st_fmt
                d["end_formatted"] = et_fmt
                d["timestamp_range"] = f"{st_fmt} - {et_fmt}"
                results.append(d)
            return results

    def find_matching_segments(self, doc_id: str, query_terms: List[str]) -> List[Dict[str, Any]]:
        """Finds specific audio segments that contain any of the query terms."""
        segments = self.get_audio_segments(doc_id)
        if not segments or not query_terms:
            return segments[:3] if segments else []

        matched = []
        lower_terms = [t.lower() for t in query_terms if len(t) > 1]
        for seg in segments:
            seg_text = seg["text"].lower()
            hit_count = sum(1 for term in lower_terms if term in seg_text)
            if hit_count > 0:
                matched.append({**seg, "hits": hit_count})

        if matched:
            matched.sort(key=lambda x: x["hits"], reverse=True)
            return matched
        return segments[:2]

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a single document by ID including its keywords and parsed metadata."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE doc_id = ?", (doc_id,))
            row = cursor.fetchone()
            if not row:
                return None

            doc = dict(row)
            cursor.execute("SELECT keyword FROM document_keywords WHERE doc_id = ?", (doc_id,))
            doc["keywords"] = [r["keyword"] for r in cursor.fetchall()]

            # Deserialize metadata_json
            raw_meta = doc.get("metadata_json")
            if raw_meta:
                try:
                    doc["parser_metadata"] = json.loads(raw_meta)
                except Exception:
                    doc["parser_metadata"] = {}
            else:
                doc["parser_metadata"] = {}

            # Attach audio segments if audio/video file
            if doc.get("file_type") in ("audio", "video"):
                doc["audio_segments"] = self.get_audio_segments(doc_id)
            else:
                doc["audio_segments"] = []

            return doc

    def get_document_by_checksum(self, checksum: str) -> Optional[Dict[str, Any]]:
        """Retrieves document by checksum to check for duplicates."""
        if not checksum:
            return None
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM documents WHERE checksum = ?", (checksum,))
            row = cursor.fetchone()
            if not row:
                return None
            doc = dict(row)
            raw_meta = doc.get("metadata_json")
            doc["parser_metadata"] = json.loads(raw_meta) if raw_meta else {}
            return doc

    def list_all_documents(self, category: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
        """Lists all documents, optionally filtered by file_type."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if category and category != "all":
                cursor.execute(
                    "SELECT * FROM documents WHERE file_type = ? ORDER BY created_at DESC LIMIT ?",
                    (category, limit)
                )
            else:
                cursor.execute(
                    "SELECT * FROM documents ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                )
            rows = cursor.fetchall()
            docs = [dict(r) for r in rows]

            # Attach keywords and parse metadata
            for d in docs:
                cursor.execute("SELECT keyword FROM document_keywords WHERE doc_id = ?", (d["doc_id"],))
                d["keywords"] = [r["keyword"] for r in cursor.fetchall()]
                raw_meta = d.get("metadata_json")
                try:
                    d["parser_metadata"] = json.loads(raw_meta) if raw_meta else {}
                except Exception:
                    d["parser_metadata"] = {}
                if d.get("file_type") in ("audio", "video"):
                    d["audio_segments"] = self.get_audio_segments(d["doc_id"])

            return docs

    def delete_document(self, doc_id: str) -> bool:
        """Deletes document and cascaded keywords from database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM document_keywords WHERE doc_id = ?", (doc_id,))
                cursor.execute("DELETE FROM documents WHERE doc_id = ?", (doc_id,))
                conn.commit()
            logger.info(f"Deleted document {doc_id} from database.")
            return True
        except Exception as e:
            logger.error(f"Error deleting document {doc_id}: {e}")
            return False

    def log_search(self, query: str, mode: str, results_count: int):
        """Records a search query in search history."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO search_history (query, search_mode, results_count) VALUES (?, ?, ?)",
                    (query, mode, results_count)
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"Failed to log search history: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Returns corpus statistics for dashboard analytics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*), SUM(word_count), SUM(file_size) FROM documents")
            total_docs, total_words, total_size = cursor.fetchone()

            cursor.execute("SELECT file_type, COUNT(*) as count FROM documents GROUP BY file_type")
            by_type = {row["file_type"]: row["count"] for row in cursor.fetchall()}

            cursor.execute("SELECT COUNT(*) FROM search_history")
            total_searches = cursor.fetchone()[0]

            return {
                "total_documents": total_docs or 0,
                "total_words": total_words or 0,
                "total_size_bytes": total_size or 0,
                "total_size_formatted": FileManager.format_file_size(total_size or 0),
                "type_breakdown": by_type,
                "total_searches": total_searches or 0
            }
