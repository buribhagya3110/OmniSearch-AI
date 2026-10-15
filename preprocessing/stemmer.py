import re
from typing import List

class PorterStemmerFallback:
    """Self-contained implementation of the Porter Stemmer algorithm (Step 1-5)."""

    def __init__(self):
        self.vowels = "aeiouy"

    def _is_consonant(self, word: str, i: int) -> bool:
        letter = word[i]
        if letter in "aeiou":
            return False
        if letter == "y":
            if i == 0:
                return True
            return not self._is_consonant(word, i - 1)
        return True

    def _m(self, word: str) -> int:
        """Measures the number of consonant sequences."""
        count = 0
        i = 0
        length = len(word)
        while i < length and self._is_consonant(word, i):
            i += 1
        while i < length:
            while i < length and not self._is_consonant(word, i):
                i += 1
            if i < length:
                count += 1
            while i < length and self._is_consonant(word, i):
                i += 1
        return count

    def stem(self, word: str) -> str:
        word = word.lower()
        if len(word) <= 2:
            return word

        # Step 1a
        if word.endswith("sses"):
            word = word[:-2]
        elif word.endswith("ies"):
            word = word[:-2]
        elif word.endswith("ss"):
            pass
        elif word.endswith("s"):
            word = word[:-1]

        # Step 1b
        if word.endswith("eed"):
            if self._m(word[:-3]) > 0:
                word = word[:-1]
        elif (word.endswith("ed") or word.endswith("ing")) and any(c in self.vowels for c in (word[:-2] if word.endswith("ed") else word[:-3])):
            word = word[:-2] if word.endswith("ed") else word[:-3]
            if word.endswith("at") or word.endswith("bl") or word.endswith("iz"):
                word += "e"
            elif len(word) >= 2 and word[-1] == word[-2] and word[-1] not in "lsz":
                word = word[:-1]

        # Step 1c
        if word.endswith("y") and any(c in self.vowels for c in word[:-1]):
            word = word[:-1] + "i"

        # Step 2 common suffixes
        suffixes = [
            ("ational", "ate"), ("tional", "tion"), ("enci", "ence"), ("anci", "ance"),
            ("izer", "ize"), ("abli", "able"), ("alli", "al"), ("entli", "ent"),
            ("eli", "e"), ("ousli", "ous"), ("ization", "ize"), ("ation", "ate"),
            ("ator", "ate"), ("alism", "al"), ("iveness", "ive"), ("fulness", "ful"),
            ("ousness", "ous"), ("aliti", "al"), ("iviti", "ive"), ("biliti", "ble")
        ]
        for suf, rep in suffixes:
            if word.endswith(suf) and self._m(word[:-len(suf)]) > 0:
                word = word[:-len(suf)] + rep
                break

        # Step 4 common suffixes
        step4_suffixes = ["al", "ance", "ence", "er", "ic", "able", "ible", "ant", "ement", "ment", "ent", "ou", "ism", "ate", "iti", "ous", "ive", "ize"]
        for suf in step4_suffixes:
            if word.endswith(suf) and self._m(word[:-len(suf)]) > 1:
                word = word[:-len(suf)]
                break

        if word.endswith("ion") and len(word) >= 4 and word[-4] in "st" and self._m(word[:-3]) > 1:
            word = word[:-3]

        return word

class Stemmer:
    """Provides stemming and lemmatization utilities."""

    def __init__(self):
        try:
            import nltk
            from nltk.stem import PorterStemmer as NLTKPorter
            self._stemmer = NLTKPorter()
            self._has_nltk = True
        except Exception:
            self._stemmer = PorterStemmerFallback()
            self._has_nltk = False

    def stem_word(self, word: str) -> str:
        """Stems an individual word."""
        if not word:
            return ""
        try:
            return self._stemmer.stem(word)
        except Exception:
            return word

    def stem_tokens(self, tokens: List[str]) -> List[str]:
        """Stems a list of words."""
        return [self.stem_word(t) for t in tokens]

    def lemmatize_word(self, word: str) -> str:
        """Lemmatizes word using WordNet if available, else stems."""
        if self._has_nltk:
            try:
                from nltk.stem import WordNetLemmatizer
                wnl = WordNetLemmatizer()
                return wnl.lemmatize(word)
            except Exception:
                pass
        return self.stem_word(word)
