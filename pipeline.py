"""
OmniSearch AI: Unified Pipeline Module
Directly maps to the System Architecture Flowchart:

[INGESTION PIPELINE]
1. User Uploads
2. File Type Detection Module
3. Parsers:
   - PDF Parser
   - DOCX Parser
   - PPT Parser
   - Image OCR (Tesseract)
   - Speech to Text (Whisper)
   - Code Parser (AST/Regex)
4. Text Extraction & Cleaning:
   - Remove Noise
   - Lowercase
   - Tokenization
   - Stopword Removal
   - Stemming/Lemmatization
5. Metadata Extraction Module:
   - Filename, File Type, Upload Date, Path, Keywords
6. Indexing Engine:
   - Whoosh (Keyword Index / BM25)
   - FAISS (Semantic Search / Vector Index)
7. SQLite Database:
   - Metadata & Index Reference

[SEARCH & RETRIEVAL PIPELINE]
8. User Search Query
9. Query Processing:
   - Tokenization
   - Spell Correction (Optional)
   - Query Expansion (Optional)
10. Search & Ranking Engine:
    - BM25 Ranking
    - Cosine Similarity (FAISS)
    - Exact Match
11. Retrieval Module:
    - Matching Files
    - Snippet Generation
    - Highlight Keywords
    - Similar Documents
12. Streamlit / Flask UI:
    - Search Results
    - Preview
    - Open File
"""

import time
from typing import Dict, Any, List, Optional
from utils.file_manager import FileManager
from utils.file_detector import FileDetector
from utils.logger import setup_logger
from extractors import extract_content, EXTRACTOR_REGISTRY
from preprocessing import preprocess_text
from metadata import MetadataExtractor
from database.database import Database
from indexing import IndexManager
from search import SearchEngine
from retrieval import ResultRetriever

logger = setup_logger("Pipeline")

class IngestionPipeline:
    """
    Executes Document Ingestion exactly matching the architecture flowchart:
    Upload -> File Detection -> Parser -> Clean/Preprocess -> Metadata -> Dual Index -> SQLite
    """

    def __init__(self):
        self.db = Database()
        self.index_manager = IndexManager()

    def process_file(
        self,
        file_bytes: bytes,
        original_filename: str,
        custom_category: Optional[str] = None
    ) -> Dict[str, Any]:
        """Runs the entire ingestion pipeline for an uploaded file."""
        trace = {
            "filename": original_filename,
            "stages": {},
            "success": False
        }
        start_time = time.time()

        try:
            # Stage 1: User Upload Storage & Checksum
            doc_id, stored_path, file_hash = FileManager.save_uploaded_file(file_bytes, original_filename)
            trace["stages"]["1_upload"] = {
                "doc_id": doc_id,
                "stored_path": stored_path,
                "sha256": file_hash,
                "file_size": len(file_bytes),
                "formatted_size": FileManager.format_file_size(len(file_bytes))
            }

            # Stage 2: File Type Detection Module
            detected_category, mime_type, extension = FileDetector.detect_file_type(stored_path)
            category = custom_category or detected_category
            trace["stages"]["2_file_type_detection"] = {
                "category": category,
                "mime_type": mime_type,
                "extension": extension
            }

            # Stage 3: Dedicated Parsers
            # (PDF Parser | DOCX Parser | PPT Parser | Image OCR | Speech to Text | Code Parser)
            parser_cls = EXTRACTOR_REGISTRY.get(category)
            parser_name = parser_cls.__name__ if parser_cls else "CodeParser (Fallback)"
            
            raw_extraction = extract_content(stored_path, category=category)
            raw_text = raw_extraction.get("text", "")
            trace["stages"]["3_parser"] = {
                "parser_used": parser_name,
                "raw_text_length": len(raw_text),
                "parser_metadata": raw_extraction.get("metadata", {})
            }

            # Stage 4: Text Extraction & Cleaning
            # (Remove Noise -> Lowercase -> Tokenization -> Stopword Removal -> Stemming/Lemmatization)
            cleaned_nlp = preprocess_text(
                raw_text,
                lowercase=True,
                remove_noise=True,
                remove_stopwords=True,
                stem=True
            )
            # Save plain text to disk
            text_path = FileManager.save_extracted_text(doc_id, raw_text)
            trace["stages"]["4_text_extraction_cleaning"] = {
                "noise_removed": True,
                "lowercased": True,
                "token_count": len(cleaned_nlp.get("tokens", [])),
                "stemmed_token_count": len(cleaned_nlp.get("stemmed_tokens", [])),
                "extracted_text_path": text_path
            }

            # Stage 5: Metadata Extraction Module
            # (Filename, File Type, Upload Date, Path, Keywords)
            metadata = MetadataExtractor.extract_metadata(
                doc_id=doc_id,
                file_path=stored_path,
                original_filename=original_filename,
                extracted_text=raw_text,
                category=category,
                parser_metadata=raw_extraction.get("metadata", {})
            )
            trace["stages"]["5_metadata_extraction"] = {
                "filename": metadata["filename"],
                "file_type": metadata["file_type"],
                "upload_date": metadata["upload_date"],
                "path": metadata["stored_path"],
                "keywords": metadata["keywords"],
                "word_count": metadata["word_count"]
            }

            # Stage 6: Indexing Engine
            # (Whoosh Keyword Index + FAISS Semantic Search Vector Index)
            faiss_index_id = self.index_manager.index_document(
                doc_id=doc_id,
                filename=original_filename,
                file_type=category,
                content=raw_text,
                keywords=metadata["keywords"]
            )
            metadata["faiss_index_id"] = faiss_index_id
            trace["stages"]["6_indexing_engine"] = {
                "whoosh_bm25_indexed": True,
                "faiss_vector_index_id": faiss_index_id
            }

            # Stage 7: SQLite Database
            # (Metadata + Index Reference)
            self.db.add_document(metadata, extracted_text_path=text_path, faiss_index_id=faiss_index_id)
            trace["stages"]["7_sqlite_database"] = {
                "doc_id": doc_id,
                "metadata_stored": True,
                "index_reference_stored": True
            }

            elapsed_ms = (time.time() - start_time) * 1000
            trace["success"] = True
            trace["elapsed_ms"] = round(elapsed_ms, 2)
            trace["doc_id"] = doc_id
            trace["metadata"] = metadata
            return trace

        except Exception as e:
            logger.error(f"Ingestion pipeline failed for {original_filename}: {e}")
            trace["success"] = False
            trace["error"] = str(e)
            return trace


    def scan_and_ingest(
        self,
        folder_path: str,
        max_file_size_mb: int = 100,
        file_types: list = None,
        skip_duplicates: bool = True
    ) -> Dict[str, Any]:
        """
        Scans a local directory and ingests all supported files into the search index.
        Skips files already indexed (by SHA-256 checksum) when skip_duplicates=True.

        Args:
            folder_path: Path to the folder to scan.
            max_file_size_mb: Maximum file size in MB to process.
            file_types: Optional filter, e.g. ["pdf", "audio"].
            skip_duplicates: If True, skip files whose checksum already exists in the database.

        Returns:
            Summary dict with counts and per-file traces.
        """
        from utils.directory_scanner import scan_directory
        from utils.file_manager import FileManager

        results = {
            "folder": folder_path,
            "total_found": 0,
            "ingested": 0,
            "skipped_duplicate": 0,
            "failed": 0,
            "traces": []
        }

        for entry in scan_directory(folder_path, max_file_size_mb=max_file_size_mb, file_types=file_types):
            results["total_found"] += 1
            file_path = entry["path"]
            filename = entry["filename"]

            try:
                with open(file_path, "rb") as f:
                    file_bytes = f.read()

                # Duplicate check via checksum
                if skip_duplicates:
                    import hashlib
                    sha = hashlib.sha256(file_bytes).hexdigest()
                    existing = self.db.get_document_by_checksum(sha)
                    if existing:
                        results["skipped_duplicate"] += 1
                        results["traces"].append({
                            "filename": filename,
                            "path": file_path,
                            "status": "skipped_duplicate",
                            "existing_doc_id": existing["doc_id"]
                        })
                        logger.info(f"Skipped duplicate: {filename} (matches {existing['doc_id']})")
                        continue

                trace = self.process_file(file_bytes, filename)
                if trace.get("success"):
                    results["ingested"] += 1
                    trace["source_path"] = file_path
                else:
                    results["failed"] += 1
                results["traces"].append(trace)

            except Exception as e:
                results["failed"] += 1
                results["traces"].append({
                    "filename": filename,
                    "path": file_path,
                    "status": "error",
                    "error": str(e)
                })
                logger.error(f"Failed to ingest {filename}: {e}")

        logger.info(
            f"Directory scan complete: {results['total_found']} found, "
            f"{results['ingested']} ingested, {results['skipped_duplicate']} duplicates skipped, "
            f"{results['failed']} failed."
        )
        return results


class SearchPipeline:
    """
    Executes Search & Retrieval exactly matching the architecture flowchart:
    User Search Query -> Query Processing -> Search & Ranking Engine -> Retrieval Module -> UI
    """

    def __init__(self):
        self.search_engine = SearchEngine()
        self.retriever = ResultRetriever()

    def search(
        self,
        query: str,
        mode: str = "hybrid",
        category: Optional[str] = None,
        top_k: int = 10,
        bm25_weight: float = 0.5,
        semantic_weight: float = 0.5,
        min_score: float = 0.0
    ) -> Dict[str, Any]:
        """Runs the search and retrieval pipeline."""
        start_time = time.time()

        # Step 1 & 2: User Search Query & Query Processing (Tokenize, Spell Check, Expansion)
        # Step 3: Search & Ranking Engine (BM25, FAISS Cosine, Exact Match)
        search_output = self.search_engine.search(
            query=query,
            mode=mode,
            category=category,
            top_k=top_k,
            bm25_weight=bm25_weight,
            semantic_weight=semantic_weight,
            min_score=min_score
        )

        # Step 4: Retrieval Module (Matching Files, Snippet Generation, Highlight Keywords, Similar Documents)
        enriched_results = self.retriever.retrieve_results(search_output, fetch_similar=True)

        elapsed_ms = (time.time() - start_time) * 1000

        return {
            "query": query,
            "mode": mode,
            "processed_query": search_output.get("processed_query", {}),
            "total_matches": len(enriched_results),
            "elapsed_ms": round(elapsed_ms, 2),
            "results": enriched_results
        }
