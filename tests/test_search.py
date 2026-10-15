import unittest
from search.query_processor import QueryProcessor
from search.search_engine import SearchEngine

class TestSearch(unittest.TestCase):

    def test_query_processor_phrase_extraction(self):
        qp = QueryProcessor()
        clean_q, phrases = qp.extract_exact_phrases('search for "machine learning" in python')
        self.assertIn("machine learning", phrases)
        self.assertNotIn('"machine learning"', clean_q)

    def test_query_processor_expansion(self):
        qp = QueryProcessor()
        res = qp.process("ai code optimization")
        self.assertTrue(len(res["expanded_terms"]) > 0)

    def test_query_processor_spelling(self):
        vocab = {"algorithm", "database", "neural", "network"}
        qp = QueryProcessor(vocabulary=vocab)
        tokens, corrected = qp.correct_spelling(["algoritm", "databaes"])
        self.assertTrue(corrected)
        self.assertEqual(tokens, ["algorithm", "database"])

    def test_search_engine_execution(self):
        se = SearchEngine()
        # Query existing documents
        res = se.search("artificial intelligence", mode="hybrid")
        self.assertIn("total_matches", res)
        self.assertIn("results", res)

if __name__ == "__main__":
    unittest.main()
