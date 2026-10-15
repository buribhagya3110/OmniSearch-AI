CREATE_DOCUMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS documents (
    doc_id TEXT PRIMARY KEY,
    filename TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    file_type TEXT NOT NULL,
    extension TEXT,
    mime_type TEXT,
    file_size INTEGER,
    file_size_formatted TEXT,
    upload_date TEXT,
    checksum TEXT,
    word_count INTEGER DEFAULT 0,
    char_count INTEGER DEFAULT 0,
    extracted_text_path TEXT,
    faiss_index_id INTEGER,
    metadata_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_KEYWORDS_TABLE = """
CREATE TABLE IF NOT EXISTS document_keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id TEXT NOT NULL,
    keyword TEXT NOT NULL,
    FOREIGN KEY(doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
);
"""

CREATE_AUDIO_SEGMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS audio_segments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_id TEXT NOT NULL,
    segment_index INTEGER NOT NULL,
    start_time REAL NOT NULL,
    end_time REAL NOT NULL,
    text TEXT NOT NULL,
    FOREIGN KEY(doc_id) REFERENCES documents(doc_id) ON DELETE CASCADE
);
"""

CREATE_SEARCH_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS search_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    search_mode TEXT NOT NULL,
    results_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_documents_file_type ON documents(file_type);
CREATE INDEX IF NOT EXISTS idx_documents_checksum ON documents(checksum);
CREATE INDEX IF NOT EXISTS idx_keywords_keyword ON document_keywords(keyword);
CREATE INDEX IF NOT EXISTS idx_keywords_doc_id ON document_keywords(doc_id);
CREATE INDEX IF NOT EXISTS idx_audio_segments_doc_id ON audio_segments(doc_id);
"""

