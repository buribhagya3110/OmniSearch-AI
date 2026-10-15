from typing import List, Dict, Any
from .text_cleaner import TextCleaner
from .tokenizer import Tokenizer
from .stopwords import StopwordFilter
from .stemmer import Stemmer

_cleaner = TextCleaner()
_tokenizer = Tokenizer()
_stopword_filter = StopwordFilter()
_stemmer = Stemmer()

def preprocess_text(
    text: str,
    lowercase: bool = True,
    remove_noise: bool = True,
    remove_stopwords: bool = True,
    stem: bool = False
) -> Dict[str, Any]:
    """
    Complete text extraction and cleaning pipeline matching the system architecture:
    1. Remove Noise
    2. Lowercase
    3. Tokenization
    4. Stopword Removal
    5. Stemming / Lemmatization (optional)
    """
    if not text:
        return {
            "cleaned_text": "",
            "tokens": [],
            "stemmed_tokens": [],
            "keywords": []
        }

    # Step 1: Remove noise & clean
    cleaned = _cleaner.clean(
        text,
        remove_html=remove_noise,
        remove_urls=remove_noise,
        lowercase=lowercase
    )

    # Step 2: Tokenization
    tokens = _tokenizer.tokenize_words(cleaned, preserve_case=not lowercase)

    # Step 3: Stopword removal
    if remove_stopwords:
        filtered_tokens = _stopword_filter.filter_tokens(tokens)
    else:
        filtered_tokens = tokens

    # Step 4: Stemming / Lemmatization
    if stem:
        processed_tokens = _stemmer.stem_tokens(filtered_tokens)
    else:
        processed_tokens = filtered_tokens

    return {
        "cleaned_text": cleaned,
        "tokens": filtered_tokens,
        "stemmed_tokens": _stemmer.stem_tokens(filtered_tokens),
        "processed_text": " ".join(processed_tokens)
    }

__all__ = [
    "TextCleaner",
    "Tokenizer",
    "StopwordFilter",
    "Stemmer",
    "preprocess_text"
]
