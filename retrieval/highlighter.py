import html
import re
from typing import List
from preprocessing import Tokenizer

class Highlighter:
    """Highlights search terms within snippets using safe HTML tags or Markdown."""

    MARK_TEMPLATE = '<mark style="background-color: #fef08a; color: #1e293b; padding: 1px 4px; border-radius: 4px; font-weight: 600;">{}</mark>'

    @classmethod
    def highlight_html(cls, text: str, query: str) -> str:
        """Highlights matching query keywords with custom HTML mark tags."""
        if not text or not query:
            return html.escape(text)

        tokens = set([t.lower() for t in Tokenizer.tokenize_words(query) if len(t) > 1])
        if not tokens:
            return html.escape(text)

        # Sort tokens by length descending so longer words match first
        sorted_tokens = sorted(tokens, key=len, reverse=True)
        escaped_tokens = [re.escape(t) for t in sorted_tokens]
        pattern = re.compile(r"\b(" + "|".join(escaped_tokens) + r")\b", re.IGNORECASE)

        # Split text into matches and non-matches to escape non-matches safely
        parts = []
        last_idx = 0
        for match in pattern.finditer(text):
            start, end = match.span()
            parts.append(html.escape(text[last_idx:start]))
            matched_word = html.escape(match.group(0))
            parts.append(cls.MARK_TEMPLATE.format(matched_word))
            last_idx = end
        parts.append(html.escape(text[last_idx:]))

        return "".join(parts)

    @classmethod
    def highlight_markdown(cls, text: str, query: str) -> str:
        """Highlights matching query keywords using Markdown bold (**word**)."""
        if not text or not query:
            return text

        tokens = set([t.lower() for t in Tokenizer.tokenize_words(query) if len(t) > 1])
        if not tokens:
            return text

        sorted_tokens = sorted(tokens, key=len, reverse=True)
        escaped_tokens = [re.escape(t) for t in sorted_tokens]
        pattern = re.compile(r"\b(" + "|".join(escaped_tokens) + r")\b", re.IGNORECASE)

        return pattern.sub(r"**\1**", text)
