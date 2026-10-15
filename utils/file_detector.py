import mimetypes
import os
from pathlib import Path
from typing import Dict, Optional, Tuple
from config import SUPPORTED_EXTENSIONS
from utils.logger import setup_logger

logger = setup_logger("FileDetector")

MAGIC_SIGNATURES = [
    (b"%PDF-", "pdf"),
    (b"\x89PNG\r\n\x1a\n", "image"),
    (b"\xff\xd8\xff", "image"),
    (b"GIF87a", "image"),
    (b"GIF89a", "image"),
    (b"BM", "image"),
    (b"II*\x00", "image"),
    (b"MM\x00*", "image"),
    (b"RIFF", "audio_or_video"),
    (b"ID3", "audio"),
    (b"\xff\xfb", "audio"),
    (b"OggS", "audio"),
    (b"fLaC", "audio"),
    (b"PK\x03\x04", "office_zip"),  # docx, pptx, or zip
]

class FileDetector:
    """Detects file type, MIME type, and category using signatures and extensions."""

    @classmethod
    def detect_category_by_extension(cls, extension: str) -> str:
        ext = extension.lower()
        if not ext.startswith("."):
            ext = f".{ext}"
        for category, extensions in SUPPORTED_EXTENSIONS.items():
            if ext in extensions:
                return category
        return "unknown"

    @classmethod
    def detect_by_magic_bytes(cls, file_path: str) -> Optional[str]:
        """Reads initial bytes to classify file format."""
        try:
            with open(file_path, "rb") as f:
                header = f.read(16)
            if not header:
                return None
            for sig, cat in MAGIC_SIGNATURES:
                if header.startswith(sig):
                    return cat
        except Exception as e:
            logger.warning(f"Failed to read magic bytes from {file_path}: {e}")
        return None

    @classmethod
    def detect_file_type(cls, file_path: str) -> Tuple[str, str, str]:
        """
        Returns (category, mime_type, extension).
        Category is one of: pdf, docx, pptx, image, audio, video, code, unknown.
        """
        path = Path(file_path)
        extension = path.suffix.lower()
        mime_type, _ = mimetypes.guess_type(str(path))
        if not mime_type:
            mime_type = "application/octet-stream"

        category = cls.detect_category_by_extension(extension)

        # Disambiguate office zip files if extension is absent or ambiguous
        if category == "unknown":
            magic_cat = cls.detect_by_magic_bytes(file_path)
            if magic_cat == "pdf":
                category = "pdf"
            elif magic_cat == "image":
                category = "image"
            elif magic_cat == "audio":
                category = "audio"
            elif magic_cat == "office_zip":
                if extension == ".pptx":
                    category = "pptx"
                elif extension == ".docx":
                    category = "docx"

        # Fallback to text/code detection if plain text file
        if category == "unknown":
            if mime_type.startswith("text/"):
                category = "code"

        return category, mime_type, extension

    @classmethod
    def is_supported(cls, file_path: str) -> bool:
        category, _, _ = cls.detect_file_type(file_path)
        return category != "unknown"
