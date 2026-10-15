import re
from typing import List

class Tokenizer:
    """Tokenizes text into words and sentences with fallback support."""

    @staticmethod
    def tokenize_words(text: str, preserve_case: bool = False) -> List[str]:
        """Splits text into individual alphanumeric and punctuation tokens."""
        if not text:
            return []
        if not preserve_case:
            text = text.lower()
        # Extracts words, hyphenated words, and alphanumeric terms
        tokens = re.findall(r"\b[a-zA-Z0-9_\-\']+\b", text)
        return tokens

    @staticmethod
    def tokenize_sentences(text: str) -> List[str]:
        """Splits text into sentences."""
        if not text:
            return []

        try:
            import nltk
            return nltk.sent_tokenize(text)
        except Exception:
            # Regex-based sentence splitter fallback
            # Splits on . ! ? followed by whitespace/capital letter or newline
            raw_sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"\'\n])|\n\n+", text)
            return [s.strip() for s in raw_sentences if s.strip()]
