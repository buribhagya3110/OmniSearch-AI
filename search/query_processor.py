import difflib
import re
from typing import List, Dict, Any, Set, Tuple, Optional
from preprocessing import preprocess_text
from utils.logger import setup_logger

logger = setup_logger("QueryProcessor")

# Common domain-specific synonym expansions
SYNONYM_MAP: Dict[str, List[str]] = {
    "doc": ["document", "file", "record"],
    "docs": ["documents", "files"],
    "pdf": ["document", "paper", "report"],
    "code": ["script", "program", "source", "function"],
    "prog": ["program", "application", "software"],
    "algo": ["algorithm", "procedure", "method"],
    "img": ["image", "picture", "photo"],
    "pic": ["picture", "image", "photo"],
    "audio": ["sound", "voice", "recording", "speech"],
    "video": ["recording", "clip", "movie"],
    "func": ["function", "method", "routine"],
    "calc": ["calculate", "computation"],
    "ai": ["artificial intelligence", "machine learning", "deep learning"],
    "ml": ["machine learning", "ai", "model"],
    "db": ["database", "table", "schema", "sqlite"]
}

class QueryProcessor:
    """Processes search queries: tokenization, phrase extraction, spell correction, expansion."""

    def __init__(self, vocabulary: Optional[Set[str]] = None):
        self.vocabulary: Set[str] = vocabulary or set()

    def update_vocabulary(self, words: List[str]):
        """Enriches spell check vocabulary from corpus words and keywords."""
        self.vocabulary.update([w.lower() for w in words if len(w) > 2])

    @staticmethod
    def extract_exact_phrases(query: str) -> Tuple[str, List[str]]:
        """Extracts quoted phrases like \"machine learning\" and returns (clean_query, phrases)."""
        phrases = re.findall(r'"([^"]+)"', query)
        # Remove quoted phrases from remainder query
        cleaned = re.sub(r'"[^"]+"', " ", query)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned, phrases

    def correct_spelling(self, tokens: List[str]) -> Tuple[List[str], bool]:
        """Suggests corrections for misspelled words based on corpus vocabulary."""
        if not self.vocabulary:
            return tokens, False

        corrected = []
        has_correction = False
        for token in tokens:
            lower = token.lower()
            if lower in self.vocabulary or len(lower) <= 3:
                corrected.append(token)
            else:
                matches = difflib.get_close_matches(lower, self.vocabulary, n=1, cutoff=0.8)
                if matches:
                    corrected.append(matches[0])
                    has_correction = True
                else:
                    corrected.append(token)

        return corrected, has_correction

    def expand_query(self, tokens: List[str]) -> List[str]:
        """Expands query tokens using the synonym dictionary."""
        expansions = []
        for token in tokens:
            lower = token.lower()
            if lower in SYNONYM_MAP:
                expansions.extend(SYNONYM_MAP[lower])
        return list(dict.fromkeys(expansions))

    def process(self, raw_query: str) -> Dict[str, Any]:
        """
        Executes full query processing pipeline:
        1. Exact phrase extraction
        2. Tokenization & cleaning
        3. Optional spell correction
        4. Query expansion
        """
        if not raw_query:
            return {
                "raw_query": "",
                "clean_query": "",
                "tokens": [],
                "exact_phrases": [],
                "corrected_query": "",
                "has_spelling_correction": False,
                "expanded_terms": []
            }

        # Step 1: Extract exact phrases
        remaining_text, exact_phrases = self.extract_exact_phrases(raw_query)

        # Step 2: Tokenization and normalization
        res = preprocess_text(
            remaining_text or raw_query,
            lowercase=True,
            remove_noise=True,
            remove_stopwords=False,
            stem=False
        )
        tokens = res.get("tokens", [])

        # Step 3: Spell correction
        corrected_tokens, has_correction = self.correct_spelling(tokens)
        corrected_query = " ".join(corrected_tokens)

        # Step 4: Query expansion
        expanded_terms = self.expand_query(tokens)

        return {
            "raw_query": raw_query,
            "clean_query": " ".join(tokens),
            "tokens": tokens,
            "exact_phrases": exact_phrases,
            "corrected_query": corrected_query if has_correction else raw_query,
            "has_spelling_correction": has_correction,
            "expanded_terms": expanded_terms
        }
