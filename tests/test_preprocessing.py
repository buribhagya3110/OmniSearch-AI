import unittest
from preprocessing import TextCleaner, Tokenizer, StopwordFilter, Stemmer, preprocess_text

class TestPreprocessing(unittest.TestCase):

    def test_text_cleaner(self):
        raw = "<p>Hello <b>World</b>! Check https://example.com/test for   details.</p>"
        cleaned = TextCleaner.clean(raw, remove_html=True, remove_urls=True)
        self.assertNotIn("<p>", cleaned)
        self.assertNotIn("https://", cleaned)
        self.assertIn("Hello World", cleaned)

    def test_tokenizer(self):
        text = "Deep learning is a subset of machine learning. It uses neural networks."
        words = Tokenizer.tokenize_words(text)
        sentences = Tokenizer.tokenize_sentences(text)
        self.assertIn("deep", words)
        self.assertIn("learning", words)
        self.assertEqual(len(sentences), 2)

    def test_stopword_filter(self):
        tokens = ["this", "is", "a", "deep", "neural", "network"]
        filtered = StopwordFilter().filter_tokens(tokens)
        self.assertNotIn("this", filtered)
        self.assertNotIn("is", filtered)
        self.assertNotIn("a", filtered)
        self.assertIn("deep", filtered)
        self.assertIn("neural", filtered)
        self.assertIn("network", filtered)

    def test_stemmer(self):
        stemmer = Stemmer()
        self.assertEqual(stemmer.stem_word("processing"), "process")
        self.assertEqual(stemmer.stem_word("networks"), "network")
        self.assertEqual(stemmer.stem_word("connections"), "connect")

    def test_preprocess_pipeline(self):
        text = "<p>Algorithms for sorting arrays efficiently.</p>"
        result = preprocess_text(text, lowercase=True, remove_noise=True, remove_stopwords=True, stem=True)
        self.assertIn("algorithm", result["stemmed_tokens"])
        self.assertIn("sort", result["stemmed_tokens"])
        self.assertNotIn("<p>", result["cleaned_text"])

if __name__ == "__main__":
    unittest.main()
