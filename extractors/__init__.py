from typing import Dict, Any
from utils.file_detector import FileDetector
from utils.logger import setup_logger

from .pdf_parser import PDFParser
from .docxx_parser import DOCXParser
from .ppt_parser import PPTParser
from .image_ocr import ImageOCR
from .audio_transcriber import AudioTranscriber
from .video_transcriber import VideoTranscriber
from .code_parser import CodeParser

logger = setup_logger("Extractors")

EXTRACTOR_REGISTRY = {
    "pdf": PDFParser,
    "docx": DOCXParser,
    "pptx": PPTParser,
    "image": ImageOCR,
    "audio": AudioTranscriber,
    "video": VideoTranscriber,
    "code": CodeParser,
}

def extract_content(file_path: str, category: str = None) -> Dict[str, Any]:
    """
    Extracts text and metadata from any supported file.
    Detects file category automatically if not provided.
    """
    if not category or category == "unknown":
        category, _, _ = FileDetector.detect_file_type(file_path)

    parser_cls = EXTRACTOR_REGISTRY.get(category)
    if not parser_cls:
        logger.warning(f"No dedicated parser found for category '{category}'. Falling back to Code/Text parser.")
        parser_cls = CodeParser

    try:
        logger.info(f"Extracting content from '{file_path}' using {parser_cls.__name__}...")
        result = parser_cls.parse(file_path)
        result["category"] = category
        return result
    except Exception as e:
        logger.error(f"Error during extraction with {parser_cls.__name__} for '{file_path}': {e}")
        return {
            "text": "",
            "category": category,
            "metadata": {"error": str(e)}
        }

__all__ = [
    "PDFParser",
    "DOCXParser",
    "PPTParser",
    "ImageOCR",
    "AudioTranscriber",
    "VideoTranscriber",
    "CodeParser",
    "extract_content",
    "EXTRACTOR_REGISTRY"
]
