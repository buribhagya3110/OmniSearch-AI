import re
import html
import unicodedata

class TextCleaner:
    """Provides utilities for cleaning, stripping noise, and normalizing text."""

    @staticmethod
    def clean(
        text: str,
        remove_html: bool = True,
        remove_urls: bool = True,
        normalize_unicode: bool = True,
        lowercase: bool = False,
        strip_special_chars: bool = False
    ) -> str:
        """Cleans input text by removing unwanted noise."""
        if not text:
            return ""

        # Normalize unicode (NFKC)
        if normalize_unicode:
            text = unicodedata.normalize("NFKC", text)

        # Unescape HTML entities
        text = html.unescape(text)

        # Remove HTML tags
        if remove_html:
            text = re.sub(r"<[^>]+>", " ", text)

        # Remove URLs
        if remove_urls:
            text = re.sub(r"https?://\S+|www\.\S+", " ", text)

        # Remove email addresses
        text = re.sub(r"\S+@\S+\.\S+", " ", text)

        # Remove control characters and non-printable characters (except newline, tab)
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)

        # Optional lowercase
        if lowercase:
            text = text.lower()

        # Optional special char removal
        if strip_special_chars:
            text = re.sub(r"[^\w\s\.\,\!\?\-]", " ", text)

        # Normalize multiple whitespace, tabs, and consecutive newlines
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n\s*\n+", "\n\n", text)

        return text.strip()
