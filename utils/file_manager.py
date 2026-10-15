import hashlib
import os
import shutil
import uuid
from pathlib import Path
from typing import Optional, Tuple
from config import UPLOAD_DIR, EXTRACTED_TEXT_DIR
from utils.logger import setup_logger

logger = setup_logger("FileManager")

class FileManager:
    """Manages file storage, persistence, hashing, and cleanup."""

    @staticmethod
    def calculate_sha256(file_path: str) -> str:
        """Calculates the SHA-256 checksum of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                sha256.update(chunk)
        return sha256.hexdigest()

    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """Formats byte size into readable string."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

    @classmethod
    def save_uploaded_file(cls, file_bytes: bytes, original_filename: str) -> Tuple[str, str, str]:
        """
        Saves uploaded file bytes into UPLOAD_DIR.
        Returns (doc_id, stored_file_path, file_hash).
        """
        doc_id = str(uuid.uuid4())
        safe_name = Path(original_filename).name.replace(" ", "_")
        stored_name = f"{doc_id}_{safe_name}"
        stored_path = UPLOAD_DIR / stored_name

        with open(stored_path, "wb") as f:
            f.write(file_bytes)

        file_hash = cls.calculate_sha256(str(stored_path))
        logger.info(f"Saved file {original_filename} as {stored_path} (ID: {doc_id})")
        return doc_id, str(stored_path), file_hash

    @classmethod
    def save_extracted_text(cls, doc_id: str, text: str) -> str:
        """Saves extracted plain text to disk."""
        text_file_path = EXTRACTED_TEXT_DIR / f"{doc_id}.txt"
        with open(text_file_path, "w", encoding="utf-8") as f:
            f.write(text)
        return str(text_file_path)

    @classmethod
    def read_extracted_text(cls, doc_id: str) -> Optional[str]:
        """Reads extracted plain text from disk."""
        text_file_path = EXTRACTED_TEXT_DIR / f"{doc_id}.txt"
        if text_file_path.exists():
            with open(text_file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        return None

    @classmethod
    def delete_document_files(cls, doc_id: str, stored_path: Optional[str] = None):
        """Removes uploaded file and extracted text file."""
        if stored_path and os.path.exists(stored_path):
            try:
                os.remove(stored_path)
            except Exception as e:
                logger.warning(f"Error removing stored file {stored_path}: {e}")

        text_file_path = EXTRACTED_TEXT_DIR / f"{doc_id}.txt"
        if text_file_path.exists():
            try:
                os.remove(text_file_path)
            except Exception as e:
                logger.warning(f"Error removing text file {text_file_path}: {e}")
