"""
OmniSearch AI: Local Directory Scanner
Recursively scans a local folder to discover and yield all supported files
for automatic ingestion into the search index.

Usage:
    CLI:  python3 app.py --scan ~/Documents/Lectures
    API:  POST /api/scan {"folder_path": "/path/to/folder"}
    UI:   "Scan Local Folder" input on the Ingest tab
"""

import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Generator, Set
from config import SUPPORTED_EXTENSIONS
from utils.file_detector import FileDetector
from utils.logger import setup_logger

logger = setup_logger("DirectoryScanner")

# Directories to always skip during recursive scan
SKIP_DIRECTORIES: Set[str] = {
    # Version control
    ".git", ".svn", ".hg",
    # Python
    "__pycache__", ".mypy_cache", ".pytest_cache", ".tox",
    "venv", ".venv", "env", ".env",
    "site-packages", "dist-packages",
    # Node / JS
    "node_modules", "bower_components", ".next", ".nuxt",
    # IDE / Editor
    ".idea", ".vscode", ".eclipse", ".settings",
    # Build outputs
    "build", "dist", "target", "out", "bin", "obj",
    # OS / System
    ".Trash", ".Spotlight-V100", ".fseventsd",
    "Library", "Applications",
    # OmniSearch own data
    "data", "database",
}

# File names to always skip
SKIP_FILES: Set[str] = {
    ".DS_Store", "Thumbs.db", "desktop.ini",
    ".gitignore", ".gitattributes",
    "package-lock.json", "yarn.lock", "poetry.lock",
}

# Default max file size: 100 MB
DEFAULT_MAX_FILE_SIZE_MB = 100


def _get_all_supported_extensions() -> Set[str]:
    """Flattens SUPPORTED_EXTENSIONS into a single set of lowercase extensions."""
    all_exts: Set[str] = set()
    for exts in SUPPORTED_EXTENSIONS.values():
        all_exts.update(exts)
    return all_exts


def _should_skip_dir(dir_name: str) -> bool:
    """Returns True if the directory should be skipped during scan."""
    # Skip hidden directories (starting with .)
    if dir_name.startswith(".") and dir_name not in {".env"}:
        return True
    # Skip known junk directories
    if dir_name in SKIP_DIRECTORIES:
        return True
    return False


def _should_skip_file(file_name: str) -> bool:
    """Returns True if the file should be skipped."""
    if file_name in SKIP_FILES:
        return True
    if file_name.startswith("."):
        return True
    return False


def scan_directory(
    folder_path: str,
    max_file_size_mb: int = DEFAULT_MAX_FILE_SIZE_MB,
    file_types: Optional[List[str]] = None
) -> Generator[Dict[str, Any], None, None]:
    """
    Recursively scans a local directory and yields metadata for each
    supported file found.

    Args:
        folder_path: Absolute or relative path to the folder to scan.
        max_file_size_mb: Skip files larger than this (default 100 MB).
        file_types: Optional filter list of categories, e.g. ["pdf", "audio"].
                    If None, all supported types are included.

    Yields:
        Dict with keys:
            - path: Absolute file path (str)
            - filename: File name (str)
            - extension: Lowercase extension including dot (str)
            - category: Detected category (str)
            - size_bytes: File size in bytes (int)
    """
    root = Path(folder_path).expanduser().resolve()
    if not root.exists():
        logger.error(f"Scan path does not exist: {root}")
        return
    if not root.is_dir():
        logger.error(f"Scan path is not a directory: {root}")
        return

    supported_exts = _get_all_supported_extensions()
    max_bytes = max_file_size_mb * 1024 * 1024
    files_found = 0
    files_skipped = 0

    logger.info(f"Starting directory scan: {root}")

    for dirpath, dirnames, filenames in os.walk(str(root), topdown=True):
        # Prune skipped directories in-place (topdown=True allows this)
        dirnames[:] = [
            d for d in dirnames if not _should_skip_dir(d)
        ]

        for fname in filenames:
            if _should_skip_file(fname):
                files_skipped += 1
                continue

            file_path = Path(dirpath) / fname
            ext = file_path.suffix.lower()

            # Check extension is supported
            if ext not in supported_exts:
                files_skipped += 1
                continue

            # Check file size
            try:
                size = file_path.stat().st_size
            except OSError:
                files_skipped += 1
                continue

            if size == 0:
                files_skipped += 1
                continue

            if size > max_bytes:
                logger.debug(f"Skipped (too large {size} bytes): {file_path}")
                files_skipped += 1
                continue

            # Detect category
            category = FileDetector.detect_category_by_extension(ext)
            if category == "unknown":
                files_skipped += 1
                continue

            # Apply category filter if specified
            if file_types and category not in file_types:
                files_skipped += 1
                continue

            files_found += 1
            yield {
                "path": str(file_path),
                "filename": fname,
                "extension": ext,
                "category": category,
                "size_bytes": size
            }

    logger.info(
        f"Directory scan complete: {root} — "
        f"{files_found} supported files found, {files_skipped} skipped."
    )


def scan_directory_summary(folder_path: str, max_file_size_mb: int = DEFAULT_MAX_FILE_SIZE_MB) -> Dict[str, Any]:
    """
    Scans a directory and returns a summary without yielding individual files.
    Useful for the UI to show a preview before committing to full ingestion.

    Returns:
        Dict with:
            - folder: scanned path
            - total_files: count of supported files
            - by_category: {category: count}
            - total_size_bytes: total size
            - files: list of {path, filename, category, size_bytes}
    """
    files = []
    by_category: Dict[str, int] = {}
    total_size = 0

    for entry in scan_directory(folder_path, max_file_size_mb=max_file_size_mb):
        files.append(entry)
        cat = entry["category"]
        by_category[cat] = by_category.get(cat, 0) + 1
        total_size += entry["size_bytes"]

    return {
        "folder": str(Path(folder_path).expanduser().resolve()),
        "total_files": len(files),
        "by_category": by_category,
        "total_size_bytes": total_size,
        "files": files
    }
