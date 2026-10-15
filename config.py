import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
EXTRACTED_TEXT_DIR = DATA_DIR / "extracted_text"
INDEX_DIR = DATA_DIR / "indexes"
DATABASE_DIR = BASE_DIR / "database"
DB_PATH = DATABASE_DIR / "metadata.db"

# Ensure all directories exist
for directory in [DATA_DIR, UPLOAD_DIR, EXTRACTED_TEXT_DIR, INDEX_DIR, DATABASE_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Supported File Extensions Mapping
SUPPORTED_EXTENSIONS = {
    "pdf": [".pdf"],
    "docx": [".docx", ".doc"],
    "pptx": [".pptx", ".ppt"],
    "image": [".png", ".jpg", ".jpeg", ".tiff", ".bmp", ".webp"],
    "audio": [".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac"],
    "video": [".mp4", ".mkv", ".mov", ".avi", ".webm"],
    "code": [
        ".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".c", ".cpp",
        ".h", ".hpp", ".cs", ".go", ".rs", ".php", ".rb", ".swift",
        ".kt", ".html", ".css", ".sql", ".sh", ".bash", ".json",
        ".yaml", ".yml", ".xml", ".md"
    ]
}

# Tesseract Configuration
TESSERACT_CMD = os.environ.get("TESSERACT_CMD", "/opt/homebrew/bin/tesseract")
if not os.path.exists(TESSERACT_CMD):
    TESSERACT_CMD = "tesseract"

# FFmpeg Configuration
FFMPEG_CMD = os.environ.get("FFMPEG_CMD", "/opt/homebrew/bin/ffmpeg")
if not os.path.exists(FFMPEG_CMD):
    FFMPEG_CMD = "ffmpeg"

# Whisper Speech-to-Text & Audio Preprocessing Configuration
WHISPER_MODEL_SIZE = os.environ.get("WHISPER_MODEL_SIZE", "tiny")
AUDIO_TARGET_SAMPLE_RATE = 16000
AUDIO_TARGET_CHANNELS = 1

# Semantic Search Embedding Configuration
EMBEDDING_MODEL_NAME = os.environ.get("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
EMBEDDING_DIM = 384

# Index File Paths
WHOOSH_INDEX_DIR = INDEX_DIR / "whoosh"
FAISS_INDEX_PATH = INDEX_DIR / "faiss_index.bin"
FAISS_METADATA_PATH = INDEX_DIR / "faiss_meta.pkl"

# Search and Ranking Parameters
DEFAULT_TOP_K = 10
BM25_WEIGHT = 0.5
SEMANTIC_WEIGHT = 0.5
EXACT_MATCH_BOOST = 1.5

# Snippet and Highlighting Settings
SNIPPET_WINDOW_CHARS = 240
MAX_SNIPPETS_PER_RESULT = 3

# Logging Settings
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
LOG_FILE = BASE_DIR / "omnisearch.log"
