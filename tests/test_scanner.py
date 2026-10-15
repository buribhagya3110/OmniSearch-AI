"""
Tests for the Local Directory Scanner module.
Tests recursive file discovery, junk directory skipping, extension filtering,
duplicate detection, and the full scan_and_ingest pipeline integration.
"""

import os
import tempfile
import unittest
import wave
import struct
import math
from pathlib import Path
from utils.directory_scanner import (
    scan_directory,
    scan_directory_summary,
    _should_skip_dir,
    _should_skip_file,
    _get_all_supported_extensions
)


class TestDirectoryScanner(unittest.TestCase):

    def setUp(self):
        """Creates a temporary directory tree with mixed file types for testing."""
        self.temp_dir = tempfile.mkdtemp()

        # Create a realistic folder structure
        # /temp_dir/
        #   notes.pdf           (supported)
        #   report.docx         (supported)
        #   photo.png           (supported)
        #   script.py           (supported)
        #   random.xyz          (unsupported)
        #   .DS_Store           (skipped system file)
        #   subfolder/
        #     slides.pptx       (supported)
        #     data.json         (supported)
        #   __pycache__/
        #     cached.pyc        (should be skipped entirely)
        #   node_modules/
        #     package.json      (should be skipped entirely)
        #   .git/
        #     HEAD              (should be skipped entirely)
        #   empty_file.pdf      (0 bytes, should be skipped)

        # Supported files
        self._create_file("notes.pdf", b"%PDF-1.4 dummy pdf content here")
        self._create_file("report.docx", b"PK\x03\x04 dummy docx content")
        self._create_file("photo.png", b"\x89PNG\r\n\x1a\n dummy image data")
        self._create_file("script.py", b"def hello():\n    print('world')\n")
        self._create_file("data.csv", b"name,age\nAlice,30\n")  # unsupported ext

        # Unsupported extension
        self._create_file("random.xyz", b"some binary data")

        # System file that should be skipped
        self._create_file(".DS_Store", b"dummy")

        # Subfolder with supported files
        os.makedirs(os.path.join(self.temp_dir, "subfolder"), exist_ok=True)
        self._create_file("subfolder/slides.pptx", b"PK\x03\x04 dummy pptx")
        self._create_file("subfolder/data.json", b'{"key": "value"}')

        # Junk directories that should be skipped
        os.makedirs(os.path.join(self.temp_dir, "__pycache__"), exist_ok=True)
        self._create_file("__pycache__/cached.pyc", b"compiled python")

        os.makedirs(os.path.join(self.temp_dir, "node_modules"), exist_ok=True)
        self._create_file("node_modules/package.json", b'{"name": "pkg"}')

        os.makedirs(os.path.join(self.temp_dir, ".git"), exist_ok=True)
        self._create_file(".git/HEAD", b"ref: refs/heads/main")

        # Empty file (should be skipped)
        self._create_file("empty_file.pdf", b"")

    def _create_file(self, rel_path: str, content: bytes):
        full_path = os.path.join(self.temp_dir, rel_path)
        with open(full_path, "wb") as f:
            f.write(content)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_supported_extensions_set(self):
        """Test that the flattened supported extensions set is non-empty and correct."""
        exts = _get_all_supported_extensions()
        self.assertIn(".pdf", exts)
        self.assertIn(".py", exts)
        self.assertIn(".mp3", exts)
        self.assertIn(".mp4", exts)
        self.assertNotIn(".xyz", exts)
        self.assertNotIn(".csv", exts)

    def test_should_skip_dir(self):
        """Test junk/hidden directory detection."""
        self.assertTrue(_should_skip_dir("__pycache__"))
        self.assertTrue(_should_skip_dir("node_modules"))
        self.assertTrue(_should_skip_dir(".git"))
        self.assertTrue(_should_skip_dir(".svn"))
        self.assertTrue(_should_skip_dir("venv"))
        self.assertTrue(_should_skip_dir(".idea"))
        self.assertFalse(_should_skip_dir("Documents"))
        self.assertFalse(_should_skip_dir("my_project"))
        self.assertFalse(_should_skip_dir("subfolder"))

    def test_should_skip_file(self):
        """Test system/junk file detection."""
        self.assertTrue(_should_skip_file(".DS_Store"))
        self.assertTrue(_should_skip_file("Thumbs.db"))
        self.assertTrue(_should_skip_file(".gitignore"))
        self.assertTrue(_should_skip_file(".hidden_file"))
        self.assertFalse(_should_skip_file("notes.pdf"))
        self.assertFalse(_should_skip_file("script.py"))

    def test_scan_directory_finds_supported_files(self):
        """Test that scan_directory finds all supported files in the temp tree."""
        results = list(scan_directory(self.temp_dir))
        filenames = [r["filename"] for r in results]

        # Should find these supported files
        self.assertIn("notes.pdf", filenames)
        self.assertIn("report.docx", filenames)
        self.assertIn("photo.png", filenames)
        self.assertIn("script.py", filenames)
        self.assertIn("slides.pptx", filenames)
        self.assertIn("data.json", filenames)

        # Should NOT find these
        self.assertNotIn("random.xyz", filenames)    # unsupported extension
        self.assertNotIn(".DS_Store", filenames)      # system file
        self.assertNotIn("empty_file.pdf", filenames) # empty file
        self.assertNotIn("cached.pyc", filenames)     # inside __pycache__
        self.assertNotIn("HEAD", filenames)            # inside .git

    def test_scan_directory_skips_junk_directories(self):
        """Test that files inside __pycache__, node_modules, .git are not returned."""
        results = list(scan_directory(self.temp_dir))
        paths = [r["path"] for r in results]

        for p in paths:
            self.assertNotIn("__pycache__", p)
            self.assertNotIn("node_modules", p)
            self.assertNotIn(".git", p)

    def test_scan_directory_result_structure(self):
        """Test that each yielded result has the expected keys."""
        results = list(scan_directory(self.temp_dir))
        self.assertTrue(len(results) > 0)

        for r in results:
            self.assertIn("path", r)
            self.assertIn("filename", r)
            self.assertIn("extension", r)
            self.assertIn("category", r)
            self.assertIn("size_bytes", r)
            self.assertTrue(r["size_bytes"] > 0)
            self.assertNotEqual(r["category"], "unknown")

    def test_scan_directory_category_filter(self):
        """Test filtering by specific file categories."""
        pdf_only = list(scan_directory(self.temp_dir, file_types=["pdf"]))
        filenames = [r["filename"] for r in pdf_only]
        self.assertIn("notes.pdf", filenames)
        self.assertNotIn("script.py", filenames)
        self.assertNotIn("photo.png", filenames)

        code_only = list(scan_directory(self.temp_dir, file_types=["code"]))
        code_filenames = [r["filename"] for r in code_only]
        self.assertIn("script.py", code_filenames)
        self.assertIn("data.json", code_filenames)
        self.assertNotIn("notes.pdf", code_filenames)

    def test_scan_directory_max_file_size(self):
        """Test that files exceeding max size are skipped."""
        # All test files are tiny, so setting max to 0 MB should skip everything
        results = list(scan_directory(self.temp_dir, max_file_size_mb=0))
        self.assertEqual(len(results), 0)

    def test_scan_directory_nonexistent_path(self):
        """Test scanning a path that does not exist returns no results."""
        results = list(scan_directory("/nonexistent/path/that/does/not/exist"))
        self.assertEqual(len(results), 0)

    def test_scan_directory_file_path_not_dir(self):
        """Test scanning a file path (not a directory) returns no results."""
        file_path = os.path.join(self.temp_dir, "notes.pdf")
        results = list(scan_directory(file_path))
        self.assertEqual(len(results), 0)

    def test_scan_directory_summary(self):
        """Test the summary function returns correct aggregate information."""
        summary = scan_directory_summary(self.temp_dir)

        self.assertEqual(summary["folder"], str(Path(self.temp_dir).resolve()))
        self.assertTrue(summary["total_files"] >= 6)
        self.assertTrue(summary["total_size_bytes"] > 0)
        self.assertIn("by_category", summary)
        self.assertIn("files", summary)

        # Check category breakdown
        cats = summary["by_category"]
        self.assertIn("pdf", cats)
        self.assertIn("code", cats)

    def test_scan_and_ingest_pipeline(self):
        """Test the full scan_and_ingest method on IngestionPipeline."""
        from unittest.mock import MagicMock, patch
        from pipeline import IngestionPipeline

        pipeline = IngestionPipeline()

        # Create a small test directory with just one file
        scan_dir = tempfile.mkdtemp()
        test_file = os.path.join(scan_dir, "hello.py")
        with open(test_file, "w") as f:
            f.write("# Sample code\ndef greet():\n    return 'hello world'\n")

        try:
            result = pipeline.scan_and_ingest(scan_dir)

            self.assertEqual(result["total_found"], 1)
            self.assertTrue(result["ingested"] >= 0)
            self.assertTrue(result["failed"] >= 0)
            self.assertEqual(
                result["ingested"] + result["skipped_duplicate"] + result["failed"],
                result["total_found"]
            )
        finally:
            import shutil
            shutil.rmtree(scan_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
