import os
from pathlib import Path
from typing import Dict, Any
from config import TESSERACT_CMD
from utils.logger import setup_logger

logger = setup_logger("ImageOCR")

class ImageOCR:
    """Extracts text from images using Tesseract OCR and PIL with preprocessing."""

    @classmethod
    def parse(cls, file_path: str) -> Dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {file_path}")

        try:
            from PIL import Image, ImageOps, ImageFilter
            import pytesseract

            # Configure tesseract executable path
            if os.path.exists(TESSERACT_CMD):
                pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

            image = Image.open(str(path))
            width, height = image.size
            format_name = image.format or path.suffix.upper().replace(".", "")
            mode = image.mode

            # Image Preprocessing for better OCR:
            # 1. Convert to grayscale
            gray = image.convert("L")
            # 2. Auto-contrast
            enhanced = ImageOps.autocontrast(gray)

            # Perform OCR on enhanced grayscale
            text = pytesseract.image_to_string(enhanced)

            # If enhanced yielded little text, try raw image as fallback
            if len(text.strip()) < 10:
                raw_text = pytesseract.image_to_string(image)
                if len(raw_text.strip()) > len(text.strip()):
                    text = raw_text

            return {
                "text": text.strip(),
                "width": width,
                "height": height,
                "format": format_name,
                "mode": mode,
                "metadata": {
                    "dimensions": f"{width}x{height}",
                    "format": format_name,
                    "mode": mode,
                    "ocr_engine": "Tesseract"
                }
            }

        except ImportError as e:
            logger.warning(f"PIL or pytesseract not available: {e}")
            return {
                "text": "",
                "metadata": {"error": "OCR libraries not installed"}
            }
        except Exception as e:
            logger.error(f"OCR failed for {file_path}: {e}")
            return {
                "text": "",
                "metadata": {"error": str(e)}
            }
