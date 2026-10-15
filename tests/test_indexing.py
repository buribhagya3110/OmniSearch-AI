import os
os.environ["OFFLINE_MODE"] = "1"
import shutil
import tempfile
import unittest
from pathlib import Path
from indexing.whoosh_index import PureBM25InvertedIndex
from indexing.faiss_index import SemanticVectorIndex

class TestIndexing(unittest.TestCase):

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_bm25_inverted_index(self):
        idx = PureBM25InvertedIndex(self.temp_dir)
        idx.add_document("doc1", "neural.txt", "code", "neural networks and deep learning algorithms", ["neural", "learning"])
        idx.add_document("doc2", "db.sql", "code", "relational database queries and joins", ["database", "sql"])

        res1 = idx.search("deep learning")
        self.assertTrue(len(res1) > 0)
        self.assertEqual(res1[0][0], "doc1")

        res2 = idx.search("relational database")
        self.assertTrue(len(res2) > 0)
        self.assertEqual(res2[0][0], "doc2")

        # Test deletion
        idx.delete_document("doc1")
        res_after = idx.search("deep learning")
        self.assertEqual(len(res_after), 0)

    def test_semantic_vector_index(self):
        v_index_path = self.temp_dir / "test_faiss.bin"
        v_meta_path = self.temp_dir / "test_faiss.pkl"
        v_idx = SemanticVectorIndex(index_path=v_index_path, meta_path=v_meta_path)

        v_idx.add_document("docA", "Autonomous vehicles computer vision and lidar navigation.")
        v_idx.add_document("docB", "Recipe for baking sourdough bread with natural yeast.")

        res = v_idx.search("self-driving cars cameras", top_k=1)
        self.assertTrue(len(res) > 0)
        self.assertEqual(res[0][0], "docA")

if __name__ == "__main__":
    unittest.main()
