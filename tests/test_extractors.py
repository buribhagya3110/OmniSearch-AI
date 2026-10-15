import tempfile
import unittest
from pathlib import Path
from extractors.code_parser import CodeParser
from utils.file_detector import FileDetector

class TestExtractors(unittest.TestCase):

    def test_file_detector_extensions(self):
        self.assertEqual(FileDetector.detect_category_by_extension(".pdf"), "pdf")
        self.assertEqual(FileDetector.detect_category_by_extension(".docx"), "docx")
        self.assertEqual(FileDetector.detect_category_by_extension(".pptx"), "pptx")
        self.assertEqual(FileDetector.detect_category_by_extension(".png"), "image")
        self.assertEqual(FileDetector.detect_category_by_extension(".mp3"), "audio")
        self.assertEqual(FileDetector.detect_category_by_extension(".mp4"), "video")
        self.assertEqual(FileDetector.detect_category_by_extension(".py"), "code")
        self.assertEqual(FileDetector.detect_category_by_extension(".js"), "code")

    def test_python_code_parser_ast(self):
        sample_code = '''
"""Module documentation for math algorithms."""

class MatrixMultiplier:
    """Performs fast matrix multiplication."""
    def multiply(self, a, b):
        """Multiplies two matrices."""
        return a * b

def compute_eigenvectors(matrix):
    """Calculates eigenvectors."""
    pass
'''
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write(sample_code)
            temp_path = f.name

        try:
            result = CodeParser.parse(temp_path)
            self.assertEqual(result["language"], "python")
            class_names = [c["name"] for c in result["classes"]]
            func_names = [fn["name"] for fn in result["functions"]]
            self.assertIn("MatrixMultiplier", class_names)
            self.assertIn("compute_eigenvectors", func_names)
            self.assertIn("multiply", func_names)
            self.assertIn("Performs fast matrix multiplication", result["text"])
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_javascript_code_parser_regex(self):
        sample_js = '''
// Main data fetching routine
function fetchData(url) {
    return fetch(url);
}

class ApiClient {
    constructor() {}
}
'''
        with tempfile.NamedTemporaryFile(suffix=".js", mode="w", delete=False) as f:
            f.write(sample_js)
            temp_path = f.name

        try:
            result = CodeParser.parse(temp_path)
            self.assertEqual(result["language"], "javascript")
            class_names = [c["name"] for c in result["classes"]]
            func_names = [fn["name"] for fn in result["functions"]]
            self.assertIn("ApiClient", class_names)
            self.assertIn("fetchData", func_names)
        finally:
            Path(temp_path).unlink(missing_ok=True)

if __name__ == "__main__":
    unittest.main()
