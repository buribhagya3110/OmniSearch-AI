"""
OmniSearch AI: Web Server (Streamlit / Flask / Built-in Web UI)
Implements the exact architecture flowchart with:
- Search Results
- Preview
- Open File / Download
- Step-by-Step Flowchart Execution Visualizer
Runs with zero external pip dependencies via Python stdlib or Flask!
"""

import cgi
import io
import json
import os
import sys
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from pipeline import IngestionPipeline, SearchPipeline
from database.database import Database
from utils.file_manager import FileManager
from utils.logger import setup_logger

logger = setup_logger("WebServer")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OmniSearch AI - Intelligent Document Search</title>
    <style>
        :root {
            --primary: #2563eb;
            --primary-hover: #1d4ed8;
            --bg: #0f172a;
            --card-bg: #1e293b;
            --card-border: #334155;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent: #38bdf8;
            --success: #10b981;
            --warning: #f59e0b;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background-color: var(--bg); color: var(--text-main); min-height: 100vh; display: flex; flex-direction: column; }
        header { background-color: rgba(30, 41, 59, 0.9); backdrop-filter: blur(8px); border-bottom: 1px solid var(--card-border); padding: 1rem 2rem; display: flex; justify-content: space-between; align-items: center; position: sticky; top: 0; z-index: 50; }
        .logo { font-size: 1.35rem; font-weight: 700; color: var(--accent); display: flex; align-items: center; gap: 0.5rem; }
        .nav-tabs { display: flex; gap: 0.5rem; }
        .nav-btn { background: transparent; border: 1px solid transparent; color: var(--text-muted); padding: 0.5rem 1rem; border-radius: 6px; cursor: pointer; font-size: 0.9rem; font-weight: 500; transition: all 0.2s; }
        .nav-btn:hover { color: var(--text-main); background: rgba(255,255,255,0.05); }
        .nav-btn.active { background: var(--primary); color: white; }
        main { flex: 1; max-width: 1200px; width: 100%; margin: 0 auto; padding: 2rem 1.5rem; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .search-hero { text-align: center; margin-bottom: 2rem; }
        .search-hero h1 { font-size: 2.2rem; margin-bottom: 0.5rem; }
        .search-hero p { color: var(--text-muted); font-size: 1rem; }
        .search-bar-wrap { display: flex; gap: 0.75rem; background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 10px; padding: 0.5rem 0.75rem; margin: 1.5rem 0; box-shadow: 0 4px 20px rgba(0,0,0,0.3); }
        .search-bar-wrap input { flex: 1; background: transparent; border: none; color: white; font-size: 1.05rem; padding: 0.5rem; outline: none; }
        .search-bar-wrap select, .search-bar-wrap button { background: #334155; color: white; border: none; border-radius: 6px; padding: 0.5rem 1rem; font-size: 0.9rem; cursor: pointer; outline: none; }
        .search-bar-wrap button { background: var(--primary); font-weight: 600; display: flex; align-items: center; gap: 0.4rem; }
        .search-bar-wrap button:hover { background: var(--primary-hover); }
        .filters-bar { display: flex; gap: 1rem; align-items: center; margin-bottom: 1.5rem; flex-wrap: wrap; }
        .chip { background: #334155; color: var(--text-muted); padding: 0.35rem 0.85rem; border-radius: 20px; font-size: 0.8rem; cursor: pointer; border: 1px solid transparent; transition: all 0.2s; }
        .chip.active, .chip:hover { color: white; border-color: var(--primary); background: rgba(37, 99, 235, 0.2); }
        .result-card { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 10px; padding: 1.25rem; margin-bottom: 1rem; transition: border-color 0.2s; }
        .result-card:hover { border-color: var(--primary); }
        .result-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.6rem; }
        .result-title { font-size: 1.15rem; font-weight: 600; color: #60a5fa; display: flex; align-items: center; gap: 0.5rem; }
        .badge { font-size: 0.75rem; padding: 0.2rem 0.5rem; border-radius: 4px; font-weight: 600; text-transform: uppercase; }
        .badge-pdf { background: #ef4444; color: white; }
        .badge-docx { background: #2563eb; color: white; }
        .badge-pptx { background: #ea580c; color: white; }
        .badge-image { background: #8b5cf6; color: white; }
        .badge-audio { background: #06b6d4; color: white; }
        .badge-video { background: #ec4899; color: white; }
        .badge-code { background: #10b981; color: white; }
        .score-pill { background: rgba(56, 189, 248, 0.15); color: var(--accent); padding: 0.25rem 0.6rem; border-radius: 12px; font-size: 0.8rem; font-weight: 700; }
        .snippet-box { background: rgba(15, 23, 42, 0.6); border-left: 3px solid var(--accent); padding: 0.75rem 1rem; border-radius: 4px; font-size: 0.92rem; line-height: 1.6; color: #cbd5e1; margin: 0.75rem 0; }
        mark { background-color: #fef08a; color: #0f172a; padding: 1px 4px; border-radius: 3px; font-weight: 600; }
        .result-meta { display: flex; gap: 1rem; font-size: 0.8rem; color: var(--text-muted); flex-wrap: wrap; margin-top: 0.5rem; align-items: center; }
        .card-actions { display: flex; gap: 0.5rem; margin-top: 0.75rem; }
        .action-btn { background: #334155; color: white; border: none; padding: 0.35rem 0.75rem; border-radius: 5px; font-size: 0.8rem; cursor: pointer; text-decoration: none; display: inline-flex; align-items: center; gap: 0.3rem; }
        .action-btn:hover { background: #475569; }
        .upload-zone { border: 2px dashed var(--card-border); border-radius: 12px; padding: 3rem 2rem; text-align: center; background: rgba(30, 41, 59, 0.4); cursor: pointer; transition: all 0.2s; margin-bottom: 1.5rem; }
        .upload-zone:hover { border-color: var(--primary); background: rgba(37, 99, 235, 0.05); }
        .upload-zone input { display: none; }
        .stage-box { background: #0f172a; border: 1px solid var(--card-border); border-radius: 8px; padding: 1rem; margin-top: 1rem; }
        .stage-step { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.5rem; font-size: 0.88rem; }
        .stage-step.done { color: var(--success); }
        .arch-diagram { background: #020617; padding: 1.5rem; border-radius: 10px; font-family: monospace; font-size: 0.8rem; line-height: 1.4; color: #38bdf8; overflow-x: auto; border: 1px solid var(--card-border); }
        .modal { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.7); z-index: 100; align-items: center; justify-content: center; padding: 1rem; }
        .modal.active { display: flex; }
        .modal-content { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 12px; max-width: 800px; width: 100%; max-height: 80vh; display: flex; flex-direction: column; overflow: hidden; }
        .modal-header { padding: 1rem 1.5rem; border-bottom: 1px solid var(--card-border); display: flex; justify-content: space-between; align-items: center; }
        .modal-body { padding: 1.5rem; overflow-y: auto; flex: 1; font-family: monospace; font-size: 0.88rem; white-space: pre-wrap; color: #e2e8f0; }
        .close-btn { background: transparent; border: none; color: var(--text-muted); font-size: 1.5rem; cursor: pointer; }
    </style>
</head>
<body>
    <header>
        <div class="logo">⚡ OmniSearch AI</div>
        <div class="nav-tabs">
            <button class="nav-btn active" onclick="switchTab('search-tab', this)">🔍 Search & Retrieval</button>
            <button class="nav-btn" onclick="switchTab('upload-tab', this)">📤 Ingest Documents</button>
            <button class="nav-btn" onclick="switchTab('library-tab', this)">📚 Document Library</button>
            <button class="nav-btn" onclick="switchTab('arch-tab', this)">🏛️ Architecture</button>
        </div>
    </header>

    <main>
        <!-- SEARCH TAB -->
        <div id="search-tab" class="tab-content active">
            <div class="search-hero">
                <h1>Universal Multi-Format Search</h1>
                <p>Hybrid BM25 Keyword Search + FAISS Cosine Semantic Search + Exact Match</p>
            </div>

            <div class="search-bar-wrap">
                <input type="text" id="queryInput" placeholder="Search across documents (e.g. machine learning, algorithms, medical notes)..." onkeydown="if(event.key==='Enter') executeSearch()">
                <select id="modeSelect">
                    <option value="hybrid">⚡ Hybrid (BM25 + FAISS)</option>
                    <option value="semantic">🧠 Semantic (FAISS)</option>
                    <option value="keyword">🔤 Keyword (BM25)</option>
                    <option value="exact">🎯 Exact Match</option>
                </select>
                <button onclick="executeSearch()">Search</button>
            </div>

            <div class="filters-bar">
                <span style="font-size: 0.85rem; color: var(--text-muted);">Format Filter:</span>
                <span class="chip active" onclick="setCategory('all', this)">All</span>
                <span class="chip" onclick="setCategory('pdf', this)">PDF</span>
                <span class="chip" onclick="setCategory('docx', this)">DOCX</span>
                <span class="chip" onclick="setCategory('pptx', this)">PPTX</span>
                <span class="chip" onclick="setCategory('code', this)">Code</span>
                <span class="chip" onclick="setCategory('image', this)">Image</span>
                <span class="chip" onclick="setCategory('audio', this)">Audio</span>
                <span class="chip" onclick="setCategory('video', this)">Video</span>
            </div>

            <div id="queryFeedback" style="margin-bottom: 1rem; color: var(--accent); font-size: 0.9rem;"></div>
            <div id="resultsMeta" style="margin-bottom: 1rem; color: var(--text-muted); font-size: 0.85rem;"></div>
            <div id="resultsContainer"></div>
        </div>

        <!-- UPLOAD TAB -->
        <div id="upload-tab" class="tab-content">
            <div class="search-hero">
                <h1>Document Ingestion Pipeline</h1>
                <p>Upload files or scan a local folder to trigger the full multi-format parsing and dual indexing pipeline.</p>
            </div>

            <div class="upload-zone" onclick="document.getElementById('fileInput').click()">
                <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">📁</div>
                <h3>Click to Select Files</h3>
                <p style="color: var(--text-muted); margin-top: 0.5rem; font-size: 0.9rem;">Supports PDF, DOCX, PPTX, Images (PNG, JPG), Audio (MP3, WAV), Video (MP4), Source Code (Python, JS, Java, C++, SQL, HTML, etc.)</p>
                <input type="file" id="fileInput" multiple onchange="handleFileUpload(this.files)">
            </div>

            <!-- LOCAL FOLDER SCANNER -->
            <div style="margin: 2rem 0; border-top: 1px solid var(--card-border); padding-top: 1.5rem;">
                <h2 style="color: var(--accent); margin-bottom: 0.5rem;">📂 Scan Local Folder</h2>
                <p style="color: var(--text-muted); font-size: 0.9rem; margin-bottom: 1rem;">Enter a folder path on your Mac to automatically discover and index all supported files inside it. Hidden folders, system files, and junk directories are skipped automatically.</p>
                <div class="search-bar-wrap">
                    <input type="text" id="folderPathInput" placeholder="Enter folder path, e.g. ~/Documents/Lectures or /Users/you/Desktop/Project" style="flex: 1;">
                    <button onclick="previewFolder()" style="background: #334155;">🔍 Preview</button>
                    <button onclick="scanFolder()">⚡ Scan &amp; Index</button>
                </div>
                <div id="scanPreview" style="margin-top: 1rem;"></div>
                <div id="scanLogs" style="margin-top: 1rem;"></div>
            </div>

            <div id="ingestionLogs"></div>
        </div>

        <!-- LIBRARY TAB -->
        <div id="library-tab" class="tab-content">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                <h2>Indexed Documents</h2>
                <button class="action-btn" onclick="loadLibrary()">🔄 Refresh</button>
            </div>
            <div id="libraryContainer"></div>
        </div>

        <!-- ARCHITECTURE TAB -->
        <div id="arch-tab" class="tab-content">
            <h2 style="margin-bottom: 1rem;">System Architecture Flowchart</h2>
            <div class="arch-diagram"><pre>
                    +----------------------+
                    |      User Uploads    |
                    |----------------------|
                    | PDF | DOCX | PPTX    |
                    | Image | Audio | Video|
                    | Source Code          |
                    +----------+-----------+
                               |
                               v
                +-----------------------------+
                | File Type Detection Module  |
                +-----------------------------+
                               |
        -----------------------------------------------------
        |        |          |         |         |           |
        v        v          v         v         v           v

    PDF Parser  DOCX      PPT Parser Image OCR  Speech      Code Parser
                Parser                (Tesseract) to Text   (AST/Regex)
                                               (Whisper)

        -----------------------------------------------------
                               |
                               v
                 +-----------------------------+
                 | Text Extraction & Cleaning  |
                 |-----------------------------|
                 | Remove Noise                |
                 | Tokenization                |
                 | Lowercase                   |
                 | Stopword Removal            |
                 | Stemming/Lemmatization      |
                 +-------------+---------------+
                               |
                               v
                 +-----------------------------+
                 | Metadata Extraction Module  |
                 |-----------------------------|
                 | Filename                    |
                 | File Type                   |
                 | Upload Date                 |
                 | Path                        |
                 | Keywords                    |
                 +-------------+---------------+
                               |
                               v
                 +-----------------------------+
                 | Indexing Engine             |
                 |-----------------------------|
                 | Whoosh (Keyword Index)      |
                 | or                          |
                 | FAISS (Semantic Search)     |
                 +-------------+---------------+
                               |
                               v
                      +------------------+
                      | SQLite Database  |
                      |------------------|
                      | Metadata         |
                      | Index Reference  |
                      +---------+--------+
                                |
=============================================================
                                |
                                v
                       User Search Query
                                |
                                v
                  +-----------------------------+
                  | Query Processing            |
                  |-----------------------------|
                  | Tokenization                |
                  | Spell Correction (Optional) |
                  | Query Expansion (Optional)  |
                  +-------------+---------------+
                                |
                                v
                 +------------------------------+
                 | Search & Ranking Engine      |
                 |------------------------------|
                 | BM25 Ranking                 |
                 | Cosine Similarity (FAISS)    |
                 | Exact Match                  |
                 +-------------+----------------+
                               |
                               v
                 +-----------------------------+
                 | Retrieval Module            |
                 |-----------------------------|
                 | Matching Files              |
                 | Snippet Generation          |
                 | Highlight Keywords          |
                 | Similar Documents           |
                 +-------------+---------------+
                               |
                               v
                    +----------------------+
                    | Streamlit / Flask UI |
                    |----------------------|
                    | Search Results       |
                    | Preview              |
                    | Open File            |
                    +----------------------+
            </pre></div>
        </div>
    </main>

    <!-- PREVIEW MODAL -->
    <div id="previewModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h3 id="modalTitle">Document Content Preview</h3>
                <button class="close-btn" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body" id="modalBody"></div>
        </div>
    </div>

    <script>
        let selectedCategory = 'all';

        function switchTab(tabId, btn) {
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            btn.classList.add('active');
            if (tabId === 'library-tab') loadLibrary();
        }

        function setCategory(cat, el) {
            selectedCategory = cat;
            document.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
            el.classList.add('active');
            executeSearch();
        }

        async function executeSearch() {
            const query = document.getElementById('queryInput').value.trim();
            if (!query) return;
            const mode = document.getElementById('modeSelect').value;

            const resMeta = document.getElementById('resultsMeta');
            const resContainer = document.getElementById('resultsContainer');
            const feedback = document.getElementById('queryFeedback');

            resContainer.innerHTML = '<p style="color: var(--text-muted);">Searching...</p>';

            try {
                const res = await fetch(`/api/search?q=${encodeURIComponent(query)}&mode=${mode}&cat=${selectedCategory}`);
                const data = await res.json();

                resMeta.textContent = `Found ${data.total_matches} match(es) in ${data.elapsed_ms}ms using ${mode.toUpperCase()} mode.`;

                // Spell / Expansion feedback
                const proc = data.processed_query || {};
                let fbHtml = '';
                if (proc.has_spelling_correction) {
                    fbHtml += `💡 Did you mean: <b>${proc.corrected_query}</b>? `;
                }
                if (proc.expanded_terms && proc.expanded_terms.length > 0) {
                    fbHtml += `🏷️ Related terms: ${proc.expanded_terms.slice(0, 5).join(', ')}`;
                }
                feedback.innerHTML = fbHtml;

                if (!data.results || data.results.length === 0) {
                    resContainer.innerHTML = '<p style="color: var(--warning); padding: 2rem; text-align: center;">No documents matched your query. Try different keywords or switch to Hybrid/Semantic mode.</p>';
                    return;
                }

                resContainer.innerHTML = data.results.map((r, i) => `
                    <div class="result-card">
                        <div class="result-header">
                            <div class="result-title">
                                <span>📄 ${r.filename}</span>
                                <span class="badge badge-${r.file_type}">${r.file_type}</span>
                                <span style="font-size: 0.75rem; color: #94a3b8;">${r.match_type.toUpperCase()}</span>
                            </div>
                            <div class="score-pill">${Math.round(r.score * 100)}% Match</div>
                        </div>

                        <div class="snippet-box">${r.highlighted_snippet_html || r.snippet}</div>

                        ${r.file_type === 'audio' || r.file_type === 'video' ? `
                            <div style="margin: 0.6rem 0; padding: 0.75rem; background: rgba(15, 23, 42, 0.7); border-radius: 8px; border: 1px solid #0891b2;">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
                                    <span style="font-size: 0.82rem; color: #22d3ee; font-weight: 600;">
                                        🎙️ Spoken Audio ${r.primary_timestamp ? `• ⏱️ Found at <b>${r.primary_timestamp}</b>` : ''}
                                    </span>
                                    <span style="font-size: 0.75rem; color: #94a3b8;">${r.audio_info?.duration_formatted ? `Duration: ${r.audio_info.duration_formatted}` : ''}</span>
                                </div>
                                <audio id="player_${r.doc_id}" controls style="width: 100%; height: 36px; border-radius: 6px;" src="/api/download/${r.doc_id}"></audio>
                                ${r.audio_info && r.audio_info.matched_segments && r.audio_info.matched_segments.length > 0 ? `
                                    <div style="margin-top: 0.5rem; display: flex; gap: 0.4rem; flex-wrap: wrap; align-items: center;">
                                        <span style="font-size: 0.75rem; color: #94a3b8;">Jump to spoken segment:</span>
                                        ${r.audio_info.matched_segments.map(seg => `
                                            <button class="action-btn" style="padding: 2px 8px; font-size: 0.75rem; background: #0e7490;" onclick="seekAudio('player_${r.doc_id}', ${seg.start})">
                                                ▶ ⏱️ ${seg.timestamp_range}
                                            </button>
                                        `).join('')}
                                    </div>
                                ` : ''}
                            </div>
                        ` : ''}

                        <div class="result-meta">
                            <span>📦 ${r.file_size_formatted || ''}</span>
                            <span>📝 ${r.word_count || 0} words</span>
                            <span>📅 ${r.upload_date ? r.upload_date.slice(0,10) : ''}</span>
                            ${r.keywords ? r.keywords.slice(0, 5).map(k => `<span style="color: #38bdf8;">#${k}</span>`).join(' ') : ''}
                        </div>

                        ${r.similar_documents && r.similar_documents.length > 0 ? `
                            <div style="font-size: 0.8rem; color: #94a3b8; margin-top: 0.5rem;">
                                🔗 Similar documents: ${r.similar_documents.map(s => `<b>${s.filename}</b> (${Math.round(s.similarity_score*100)}%)`).join(' | ')}
                            </div>
                        ` : ''}

                        <div class="card-actions">
                            <button class="action-btn" onclick="previewDoc('${r.doc_id}', '${r.filename}')">🔍 Preview Transcript</button>
                            <a class="action-btn" href="/api/download/${r.doc_id}" download>⬇️ Open / Download Audio</a>
                        </div>
                    </div>
                `).join('');

            } catch (err) {
                resContainer.innerHTML = `<p style="color: #ef4444;">Search Error: ${err}</p>`;
            }
        }

        async function handleFileUpload(files) {
            if (!files || files.length === 0) return;
            const logBox = document.getElementById('ingestionLogs');
            logBox.innerHTML = '';

            for (let i = 0; i < files.length; i++) {
                const file = files[i];
                const card = document.createElement('div');
                card.className = 'stage-box';
                card.innerHTML = `<h4>Ingesting: ${file.name}</h4><p style="color: var(--text-muted); font-size: 0.85rem;">Processing through architecture pipeline...</p>`;
                logBox.appendChild(card);

                const formData = new FormData();
                formData.append('file', file);

                try {
                    const res = await fetch('/api/upload', { method: 'POST', body: formData });
                    const trace = await res.json();
                    if (trace.success) {
                        const s = trace.stages;
                        card.innerHTML = `
                            <h4 style="color: var(--success);">✅ Ingested: ${file.name} in ${trace.elapsed_ms}ms</h4>
                            <div class="stage-step done">✓ 1. File Type Detection: <b>${s['2_file_type_detection'].category.toUpperCase()}</b> (${s['2_file_type_detection'].mime_type})</div>
                            <div class="stage-step done">✓ 2. Parser Module: <b>${s['3_parser'].parser_used}</b> (Extracted ${s['3_parser'].raw_text_length} chars)</div>
                            <div class="stage-step done">✓ 3. Text Extraction & Cleaning: Noise removed, Lowercase, Stopwords, Stemming (${s['4_text_extraction_cleaning'].token_count} tokens)</div>
                            <div class="stage-step done">✓ 4. Metadata Extraction: Keywords: <i>${s['5_metadata_extraction'].keywords.slice(0, 5).join(', ')}</i></div>
                            <div class="stage-step done">✓ 5. Indexing Engine: Whoosh BM25 & FAISS Vector Index (ID: ${s['6_indexing_engine'].faiss_vector_index_id})</div>
                            <div class="stage-step done">✓ 6. SQLite Database: Metadata & Index Reference Saved</div>
                        `;
                    } else {
                        card.innerHTML = `<h4 style="color: #ef4444;">❌ Failed: ${file.name}</h4><p style="color: #fca5a5;">${trace.error}</p>`;
                    }
                } catch (err) {
                    card.innerHTML = `<h4 style="color: #ef4444;">❌ Upload Error: ${err}</h4>`;
                }
            }
        }

        async function loadLibrary() {
            const container = document.getElementById('libraryContainer');
            container.innerHTML = '<p style="color: var(--text-muted);">Loading indexed documents...</p>';
            try {
                const res = await fetch('/api/documents');
                const docs = await res.json();
                if (!docs || docs.length === 0) {
                    container.innerHTML = '<p style="color: var(--text-muted);">No documents indexed yet. Use the "Ingest Documents" tab to add files.</p>';
                    return;
                }
                container.innerHTML = docs.map(d => `
                    <div class="result-card">
                        <div class="result-header">
                            <div class="result-title">
                                <span>📄 ${d.filename}</span>
                                <span class="badge badge-${d.file_type}">${d.file_type}</span>
                            </div>
                            <span style="font-size: 0.85rem; color: var(--text-muted);">${d.file_size_formatted}</span>
                        </div>
                        <div class="result-meta">
                            <span>Words: ${d.word_count}</span>
                            <span>Checksum: ${d.checksum.slice(0, 16)}...</span>
                            <span>Uploaded: ${d.upload_date ? d.upload_date.slice(0, 19) : ''}</span>
                        </div>
                        <div class="card-actions">
                            <button class="action-btn" onclick="previewDoc('${d.doc_id}', '${d.filename}')">🔍 Preview</button>
                            <a class="action-btn" href="/api/download/${d.doc_id}" download>⬇️ Download</a>
                            <button class="action-btn" style="background: #ef4444;" onclick="deleteDoc('${d.doc_id}')">🗑️ Delete</button>
                        </div>
                    </div>
                `).join('');
            } catch (err) {
                container.innerHTML = `<p style="color: #ef4444;">Error loading library: ${err}</p>`;
            }
        }

        async function previewDoc(docId, filename) {
            document.getElementById('modalTitle').textContent = `Content Preview: ${filename}`;
            document.getElementById('modalBody').textContent = 'Loading text...';
            document.getElementById('previewModal').classList.add('active');
            try {
                const res = await fetch(`/api/preview/${docId}`);
                const data = await res.json();
                document.getElementById('modalBody').textContent = data.text || '(No text content extracted)';
            } catch (err) {
                document.getElementById('modalBody').textContent = 'Error loading preview.';
            }
        }

        function seekAudio(playerId, seconds) {
            const player = document.getElementById(playerId);
            if (player) {
                player.currentTime = Math.max(0, seconds - 0.5);
                player.play();
            }
        }

        function closeModal() {
            document.getElementById('previewModal').classList.remove('active');
        }

        async function deleteDoc(docId) {
            if (!confirm('Are you sure you want to delete this document from the index and database?')) return;
            await fetch(`/api/documents/${docId}`, { method: 'DELETE' });
            loadLibrary();
        }

        async function previewFolder() {
            const folderPath = document.getElementById('folderPathInput').value.trim();
            if (!folderPath) { alert('Please enter a folder path.'); return; }
            const preview = document.getElementById('scanPreview');
            preview.innerHTML = '<p style="color: var(--text-muted);">🔍 Scanning folder for supported files...</p>';
            try {
                const res = await fetch('/api/scan/preview', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ folder_path: folderPath })
                });
                const data = await res.json();
                if (!data.success) {
                    preview.innerHTML = `<p style="color: #ef4444;">\u274c ${data.error}</p>`;
                    return;
                }
                if (data.total_files === 0) {
                    preview.innerHTML = '<p style="color: var(--warning);">No supported files found in this directory.</p>';
                    return;
                }
                let catHtml = Object.entries(data.by_category).sort().map(([cat, count]) =>
                    `<span class="chip">${cat.toUpperCase()}: ${count}</span>`
                ).join(' ');
                preview.innerHTML = `
                    <div class="result-card">
                        <div class="result-header">
                            <div class="result-title">\ud83d\udcc2 ${data.folder}</div>
                            <div class="score-pill">${data.total_files} files \u2022 ${data.total_size_formatted}</div>
                        </div>
                        <div style="margin: 0.75rem 0; display: flex; gap: 0.5rem; flex-wrap: wrap;">${catHtml}</div>
                        <div style="max-height: 200px; overflow-y: auto; font-size: 0.82rem; color: var(--text-muted);">
                            ${data.files.slice(0, 50).map(f => `<div>\u2022 ${f.filename} <span style="color: #64748b;">(${f.category})</span></div>`).join('')}
                            ${data.total_files > 50 ? `<div style="color: var(--accent);">... and ${data.total_files - 50} more files</div>` : ''}
                        </div>
                    </div>
                `;
            } catch (err) {
                preview.innerHTML = `<p style="color: #ef4444;">Error: ${err}</p>`;
            }
        }

        async function scanFolder() {
            const folderPath = document.getElementById('folderPathInput').value.trim();
            if (!folderPath) { alert('Please enter a folder path.'); return; }
            if (!confirm(`This will scan and index all supported files in:\\n${folderPath}\\n\\nDuplicate files will be automatically skipped. Continue?`)) return;

            const logBox = document.getElementById('scanLogs');
            logBox.innerHTML = `
                <div class="stage-box">
                    <h4 style="color: var(--accent);">\u26a1 Scanning & indexing: ${folderPath}</h4>
                    <p style="color: var(--text-muted); font-size: 0.85rem;">This may take a while for large folders. Processing through the full pipeline for each file...</p>
                </div>
            `;
            try {
                const res = await fetch('/api/scan', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ folder_path: folderPath })
                });
                const data = await res.json();
                if (!data.success) {
                    logBox.innerHTML = `<div class="stage-box"><h4 style="color: #ef4444;">\u274c ${data.error}</h4></div>`;
                    return;
                }
                let traceHtml = (data.traces || []).map(t => {
                    const ok = t.success || t.status === 'skipped_duplicate';
                    const icon = t.success ? '\u2705' : t.status === 'skipped_duplicate' ? '\u23ed\ufe0f' : '\u274c';
                    const detail = t.status === 'skipped_duplicate' ? 'duplicate' : t.success ? `${t.elapsed_ms}ms` : (t.error || 'failed');
                    return `<div class="stage-step ${ok ? 'done' : ''}">${icon} ${t.filename} \u2014 <span style="color: #64748b;">${detail}</span></div>`;
                }).join('');
                logBox.innerHTML = `
                    <div class="stage-box">
                        <h4 style="color: var(--success);">\ud83c\udf89 Scan Complete!</h4>
                        <div class="result-meta" style="margin: 0.75rem 0;">
                            <span>\ud83d\udcc4 Found: ${data.total_found}</span>
                            <span>\u2705 Ingested: ${data.ingested}</span>
                            <span>\u23ed\ufe0f Duplicates: ${data.skipped_duplicate}</span>
                            <span>\u274c Failed: ${data.failed}</span>
                        </div>
                        <div style="max-height: 300px; overflow-y: auto;">${traceHtml}</div>
                    </div>
                `;
            } catch (err) {
                logBox.innerHTML = `<div class="stage-box"><h4 style="color: #ef4444;">\u274c Scan Error: ${err}</h4></div>`;
            }
        }

        // Auto-run search on load
        window.addEventListener('DOMContentLoaded', () => {
            document.getElementById('queryInput').value = 'machine learning';
            executeSearch();
        });
    </script>
</body>
</html>
"""

class OmniSearchHandler(BaseHTTPRequestHandler):
    """Zero-dependency HTTP request handler serving the Web UI and REST APIs."""

    ingestion_pipeline = IngestionPipeline()
    search_pipeline = SearchPipeline()
    db = Database()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        # 1. Main Web UI
        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))

        # 2. Search API: /api/search?q=...&mode=...&cat=...
        elif path == "/api/search":
            query = params.get("q", [""])[0]
            mode = params.get("mode", ["hybrid"])[0]
            cat = params.get("cat", [None])[0]
            category = None if cat == "all" else cat

            res = self.search_pipeline.search(query=query, mode=mode, category=category)
            self._send_json(res)

        # 3. List Documents API: /api/documents
        elif path == "/api/documents":
            docs = self.db.list_all_documents()
            self._send_json(docs)

        # 4. Preview Extracted Text API: /api/preview/<doc_id>
        elif path.startswith("/api/preview/"):
            doc_id = path.replace("/api/preview/", "")
            text = FileManager.read_extracted_text(doc_id) or ""
            self._send_json({"doc_id": doc_id, "text": text})

        # 5. Open / Download File API: /api/download/<doc_id>
        elif path.startswith("/api/download/"):
            doc_id = path.replace("/api/download/", "")
            doc = self.db.get_document(doc_id)
            if doc and os.path.exists(doc.get("stored_path", "")):
                stored_path = doc["stored_path"]
                filename = doc.get("filename", Path(stored_path).name)
                self.send_response(200)
                self.send_header("Content-Type", doc.get("mime_type", "application/octet-stream"))
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
                self.send_header("Content-Length", str(os.path.getsize(stored_path)))
                self.end_headers()
                with open(stored_path, "rb") as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "Document not found")

        else:
            self.send_error(404, "Endpoint not found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)

        # File Upload Ingestion API: /api/upload
        if parsed.path == "/api/upload":
            content_type = self.headers.get("Content-Type", "")
            if not content_type.startswith("multipart/form-data"):
                self.send_error(400, "Expected multipart/form-data")
                return

            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": content_type}
            )

            if "file" not in form:
                self.send_error(400, "Missing 'file' parameter")
                return

            file_item = form["file"]
            filename = file_item.filename or "uploaded_file"
            file_bytes = file_item.file.read()

            trace = self.ingestion_pipeline.process_file(file_bytes, filename)
            self._send_json(trace)

        # Local Directory Scan API: /api/scan
        elif parsed.path == "/api/scan":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8") if content_length else "{}"
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                self.send_error(400, "Invalid JSON body")
                return

            folder_path = payload.get("folder_path", "").strip()
            if not folder_path:
                self._send_json({"success": False, "error": "Missing 'folder_path' in request body."})
                return

            folder = os.path.expanduser(folder_path)
            if not os.path.isdir(folder):
                self._send_json({"success": False, "error": f"'{folder}' is not a valid directory."})
                return

            result = self.ingestion_pipeline.scan_and_ingest(folder)
            result["success"] = True
            self._send_json(result)

        # Local Directory Preview API: /api/scan/preview
        elif parsed.path == "/api/scan/preview":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8") if content_length else "{}"
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                self.send_error(400, "Invalid JSON body")
                return

            folder_path = payload.get("folder_path", "").strip()
            if not folder_path:
                self._send_json({"success": False, "error": "Missing 'folder_path' in request body."})
                return

            folder = os.path.expanduser(folder_path)
            if not os.path.isdir(folder):
                self._send_json({"success": False, "error": f"'{folder}' is not a valid directory."})
                return

            from utils.directory_scanner import scan_directory_summary
            from utils.file_manager import FileManager
            summary = scan_directory_summary(folder)
            summary["success"] = True
            summary["total_size_formatted"] = FileManager.format_file_size(summary["total_size_bytes"])
            # Limit file list to first 200 for UI display
            summary["files"] = summary["files"][:200]
            self._send_json(summary)

        else:
            self.send_error(404, "Endpoint not found")

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path.startswith("/api/documents/"):
            doc_id = parsed.path.replace("/api/documents/", "")
            doc = self.db.get_document(doc_id)
            if doc:
                from indexing import IndexManager
                IndexManager().delete_document(doc_id)
                self.db.delete_document(doc_id)
                FileManager.delete_document_files(doc_id, doc.get("stored_path"))
                self._send_json({"success": True, "deleted": doc_id})
            else:
                self.send_error(404, "Document not found")
        else:
            self.send_error(404, "Endpoint not found")

    def _send_json(self, data: Any):
        payload = json.dumps(data, default=str).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format, *args):
        # Clean logging
        logger.info(f"{self.address_string()} - {format % args}")


def run_server(port: int = 5000):
    server_address = ("127.0.0.1", port)
    httpd = HTTPServer(server_address, OmniSearchHandler)
    print("=" * 65)
    print("⚡ OmniSearch AI Web Server is running!")
    print(f"👉 Open in your browser: http://localhost:{port}")
    print("=" * 65)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    run_server(port)
