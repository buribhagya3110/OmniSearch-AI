import collections
import datetime
import math
from pathlib import Path
from typing import Dict, Any, List
from utils.file_manager import FileManager
from utils.file_detector import FileDetector
from preprocessing import preprocess_text
from utils.logger import setup_logger

logger = setup_logger("MetadataExtractor")

class MetadataExtractor:
    """Extracts file attributes, timestamps, checksums, and keywords."""

    @staticmethod
    def extract_keywords(text: str, top_n: int = 10) -> List[str]:
        """Extracts top salient keywords using term frequency and stopword filtering."""
        if not text:
            return []

        # Run preprocessing to get clean, stopword-filtered tokens
        res = preprocess_text(text, lowercase=True, remove_noise=True, remove_stopwords=True, stem=False)
        tokens = [t for t in res.get("tokens", []) if len(t) > 2 and not t.isnumeric()]

        if not tokens:
            return []

        counts = collections.Counter(tokens)
        total_tokens = len(tokens)

        # Score by TF with slight length penalty discount for extremely short terms
        scored = []
        for word, count in counts.items():
            tf = count / total_tokens
            # Bonus for words with medium length (domain terminology)
            bonus = 1.2 if 4 <= len(word) <= 15 else 1.0
            scored.append((word, tf * bonus))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [word for word, score in scored[:top_n]]

    @classmethod
    def extract_metadata(
        cls,
        doc_id: str,
        file_path: str,
        original_filename: str,
        extracted_text: str = "",
        category: str = None,
        parser_metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Compiles complete metadata record matching the architecture specification."""
        path = Path(file_path)
        stat = path.stat() if path.exists() else None

        file_size_bytes = stat.st_size if stat else 0
        file_size_formatted = FileManager.format_file_size(file_size_bytes)
        upload_date = datetime.datetime.now().isoformat()
        checksum = FileManager.calculate_sha256(file_path) if path.exists() else ""

        if not category or category == "unknown":
            category, mime_type, extension = FileDetector.detect_file_type(file_path)
        else:
            extension = path.suffix.lower()
            mime_type = "application/octet-stream"

        word_count = len(extracted_text.split()) if extracted_text else 0
        char_count = len(extracted_text) if extracted_text else 0
        keywords = cls.extract_keywords(extracted_text, top_n=10)

        metadata = {
            "doc_id": doc_id,
            "filename": original_filename,
            "stored_path": str(path.resolve()),
            "file_type": category,
            "extension": extension,
            "mime_type": mime_type,
            "file_size": file_size_bytes,
            "file_size_formatted": file_size_formatted,
            "upload_date": upload_date,
            "checksum": checksum,
            "word_count": word_count,
            "char_count": char_count,
            "keywords": keywords,
            "parser_metadata": parser_metadata or {}
        }
        return metadata
