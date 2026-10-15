import re
from typing import List
from config import SNIPPET_WINDOW_CHARS
from preprocessing import Tokenizer

class SnippetGenerator:
    """Generates context-aware snippets around query terms or dense informative passages."""

    @staticmethod
    def generate_snippet(
        text: str,
        query: str,
        window_chars: int = SNIPPET_WINDOW_CHARS,
        max_snippets: int = 2
    ) -> str:
        """
        Extracts relevant text snippets around query terms.
        Falls back to document beginning if no direct term match.
        """
        if not text:
            return ""

        query_tokens = [t.lower() for t in Tokenizer.tokenize_words(query) if len(t) > 2]
        if not query_tokens:
            # Return first window of text
            snippet = text[:window_chars].strip()
            return f"{snippet}..." if len(text) > window_chars else snippet

        # Find best match locations
        text_lower = text.lower()
        match_indices = []
        for token in query_tokens:
            for match in re.finditer(r"\b" + re.escape(token) + r"\b", text_lower):
                match_indices.append(match.start())

        if not match_indices:
            # Try substring search if word boundary failed
            for token in query_tokens:
                pos = text_lower.find(token)
                if pos != -1:
                    match_indices.append(pos)

        if not match_indices:
            snippet = text[:window_chars].strip()
            return f"{snippet}..." if len(text) > window_chars else snippet

        match_indices.sort()
        snippets = []
        half_window = window_chars // 2

        used_ranges = []
        for idx in match_indices:
            if len(snippets) >= max_snippets:
                break

            start = max(0, idx - half_window)
            end = min(len(text), idx + half_window)

            # Snap to word boundaries
            if start > 0:
                space_before = text.rfind(" ", max(0, start - 20), start)
                if space_before != -1:
                    start = space_before + 1

            if end < len(text):
                space_after = text.find(" ", end, min(len(text), end + 20))
                if space_after != -1:
                    end = space_after

            # Check overlap with existing ranges
            overlaps = any(not (end < r[0] or start > r[1]) for r in used_ranges)
            if not overlaps:
                used_ranges.append((start, end))
                chunk = text[start:end].strip().replace("\n", " ")
                prefix = "... " if start > 0 else ""
                suffix = " ..." if end < len(text) else ""
                snippets.append(f"{prefix}{chunk}{suffix}")

        return " <br> ".join(snippets) if snippets else text[:window_chars]
