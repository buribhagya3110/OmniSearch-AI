import unittest
from retrieval.snippet_generator import SnippetGenerator
from retrieval.highlighter import Highlighter

class TestRetrieval(unittest.TestCase):

    def test_snippet_generator(self):
        text = (
            "Introduction to computer systems. Memory management is crucial for high performance. "
            "In this chapter, we discuss the garbage collection algorithm and how it optimizes heap allocation. "
            "Finally, we analyze performance benchmarks across multiple architectures."
        )
        snippet = SnippetGenerator.generate_snippet(text, query="garbage collection", window_chars=80)
        self.assertIn("garbage collection", snippet)

    def test_highlighter_html(self):
        snippet = "Neural networks power modern image classification models."
        highlighted = Highlighter.highlight_html(snippet, query="neural networks")
        self.assertIn("<mark", highlighted)
        self.assertIn("Neural", highlighted)
        self.assertIn("networks", highlighted)

    def test_highlighter_markdown(self):
        snippet = "Quick sort is an efficient sorting algorithm."
        highlighted = Highlighter.highlight_markdown(snippet, query="sorting algorithm")
        self.assertIn("**sorting**", highlighted)
        self.assertIn("**algorithm**", highlighted)

if __name__ == "__main__":
    unittest.main()
