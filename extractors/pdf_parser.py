import re
from pathlib import Path
from typing import Dict, Any, List
from utils.logger import setup_logger

logger = setup_logger("PDFParser")

class PDFParser:
    """Extracts text and metadata from PDF files with fallback support."""

    @classmethod
    def parse(cls, file_path: str) -> Dict[str, Any]:
        """
        Parses a PDF file and returns extracted text and metadata.
        Returns: {
            "text": str,
            "pages": List[str],
            "total_pages": int,
            "metadata": dict
        }
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        # Attempt 1: pypdf / PyPDF2
        try:
            import pypdf
            reader = pypdf.PdfReader(str(path))
            pages_text = []
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                pages_text.append(page_text)
            
            raw_meta = reader.metadata or {}
            metadata = {
                "title": raw_meta.get("/Title", "") or "",
                "author": raw_meta.get("/Author", "") or "",
                "creator": raw_meta.get("/Creator", "") or "",
                "producer": raw_meta.get("/Producer", "") or "",
                "total_pages": len(reader.pages)
            }
            full_text = "\n\n".join(pages_text).strip()
            return {
                "text": full_text,
                "pages": pages_text,
                "total_pages": len(reader.pages),
                "metadata": metadata
            }
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"pypdf extraction failed for {file_path}: {e}. Trying fallback.")

        # Attempt 2: PyMuPDF / fitz
        try:
            import fitz
            doc = fitz.open(str(path))
            pages_text = [page.get_text() for page in doc]
            full_text = "\n\n".join(pages_text).strip()
            return {
                "text": full_text,
                "pages": pages_text,
                "total_pages": len(doc),
                "metadata": doc.metadata or {}
            }
        except ImportError:
            pass
        except Exception as e:
            logger.warning(f"fitz extraction failed for {file_path}: {e}. Trying fallback.")

        # Attempt 3: Pure-Python regex/stream fallback for basic PDF text
        try:
            with open(path, "rb") as f:
                content = f.read()
            # Extract plain text from PDF stream blocks: BT ... ET
            stream_matches = re.findall(rb"BT[\s\S]*?ET", content)
            extracted_words = []
            for block in stream_matches:
                # Find text inside parentheses: (text)
                strings = re.findall(rb"\((.*?)\)", block)
                for s in strings:
                    try:
                        extracted_words.append(s.decode("utf-8", errors="ignore"))
                    except Exception:
                        pass
            extracted_text = " ".join(extracted_words).strip()
            return {
                "text": extracted_text,
                "pages": [extracted_text],
                "total_pages": 1,
                "metadata": {"fallback": True}
            }
        except Exception as e:
            logger.error(f"Fallback PDF parsing failed for {file_path}: {e}")
            return {
                "text": "",
                "pages": [],
                "total_pages": 0,
                "metadata": {"error": str(e)}
            }
