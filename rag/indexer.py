"""
Document Indexer — Full pipeline from parsed documents to indexed storage.
"""
import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional

from .config import (
    STORES_DIR, METADATA_DB_PATH, INDEX_REGISTRY_PATH,
    LITERATURE_PATHS, METADATA_SCHEMA, SUPPORTED_FORMATS,
)
from .pdf_parser import PDFParser, ParsedDocument
from .chunker import AcademicChunker


class DocumentIndexer:
    """Document indexer — manages the full parse-to-store pipeline."""

    def __init__(self, db_path: str = ""):
        self.parser = PDFParser()
        self._db_path = db_path or str(METADATA_DB_PATH)
        self._init_metadata_db()
        self._init_index_registry()

    def _init_metadata_db(self):
        """Initialize SQLite metadata database."""
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self._db_path)
        self.db.executescript(METADATA_SCHEMA)
        self.db.commit()

    def _init_index_registry(self):
        """Initialize index registry."""
        if INDEX_REGISTRY_PATH.exists():
            with open(INDEX_REGISTRY_PATH, 'r', encoding='utf-8') as f:
                self.registry = json.load(f)
        else:
            self.registry = {
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
                "collections": {},
                "stats": {"total_documents": 0, "total_chunks": 0}
            }
            self._save_registry()

    def _save_registry(self):
        """Save index registry to disk."""
        INDEX_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(INDEX_REGISTRY_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.registry, f, ensure_ascii=False, indent=2)

    def _generate_doc_id(self, file_path: str) -> str:
        """Generate unique document ID."""
        return hashlib.md5(file_path.encode()).hexdigest()[:16]

    def index_document(self, file_path: str, collection: str = "papers",
                       doc_type: str = "paper", discipline: str = "general",
                       topic_cluster: str = "") -> dict:
        """
        Index a single document.

        Args:
            file_path: Path to the document file
            collection: Collection name (papers, books, notes, etc.)
            doc_type: Document type (paper, book, policy, note, etc.)
            discipline: Academic discipline
            topic_cluster: Topic cluster label

        Returns:
            dict: Indexing result
        """
        path = Path(file_path)
        doc_id = self._generate_doc_id(str(path))

        if self._is_indexed(doc_id):
            return {"status": "skipped", "reason": "already indexed", "doc_id": doc_id}

        try:
            parsed = self.parser.parse(str(path))
        except Exception as e:
            return {"status": "error", "reason": f"parse failed: {e}", "doc_id": doc_id}

        chunker_type = {
            "paper": "academic_paper",
            "book": "book_notes",
            "policy": "policy_document",
            "speech": "speech",
            "note": "reading_card",
        }.get(doc_type, "academic_paper")

        chunker = AcademicChunker(chunker_type)
        chunks = chunker.chunk_document(parsed)

        citation_key = self._generate_citation_key(parsed)

        self._store_metadata(doc_id, parsed, collection, doc_type,
                            discipline, topic_cluster, citation_key, len(chunks))
        self._store_chunks(doc_id, chunks)
        self._update_registry(collection, doc_id, str(path))

        return {
            "status": "success",
            "doc_id": doc_id,
            "title": parsed.title,
            "chunks": len(chunks),
            "language": parsed.language,
            "citation_key": citation_key,
        }

    def index_collection(self, collection: str, directory: Optional[str] = None) -> dict:
        """
        Batch index a collection from a directory.

        Args:
            collection: Collection name
            directory: Directory path (defaults to config)

        Returns:
            dict: Batch indexing results
        """
        if directory is None:
            directory = str(LITERATURE_PATHS.get(collection, ""))

        if not directory or not Path(directory).exists():
            return {"status": "error", "reason": f"directory not found: {directory}"}

        doc_type_map = {
            "papers": "paper", "papers_cn": "paper", "papers_en": "paper",
            "books": "book", "policies": "policy",
            "notes": "note", "deep_reads": "note",
        }
        doc_type = doc_type_map.get(collection, "paper")

        results = {"success": 0, "skipped": 0, "error": 0, "details": []}

        for ext in SUPPORTED_FORMATS:
            for file_path in Path(directory).glob(f"**/*{ext}"):
                if any(skip in str(file_path) for skip in ['chroma_db', '__pycache__', '.DS_Store']):
                    continue
                result = self.index_document(str(file_path), collection, doc_type)
                results[result["status"]] = results.get(result["status"], 0) + 1
                results["details"].append(result)
                print(f"  [{result['status']}] {file_path.name}")

        return results

    def _is_indexed(self, doc_id: str) -> bool:
        cursor = self.db.execute("SELECT id FROM documents WHERE id = ?", (doc_id,))
        return cursor.fetchone() is not None

    def _store_metadata(self, doc_id, parsed, collection, doc_type,
                       discipline, topic_cluster, citation_key, chunk_count):
        self.db.execute("""
            INSERT OR REPLACE INTO documents
            (id, title, authors, year, keywords, discipline, topic_cluster,
             language, doc_type, file_path, chunk_count, citation_key,
             abstract, source_collection)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc_id, parsed.title, parsed.authors, parsed.year,
            ','.join(parsed.keywords), discipline, topic_cluster,
            parsed.language, doc_type, parsed.file_path, chunk_count,
            citation_key, parsed.abstract, collection
        ))
        self.db.commit()

    def _store_chunks(self, doc_id: str, chunks: list):
        for chunk in chunks:
            chunk_id = f"{doc_id}_{chunk.chunk_index:04d}"
            self.db.execute("""
                INSERT OR REPLACE INTO chunks
                (id, document_id, chunk_index, content, section_name, token_count)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                chunk_id, doc_id, chunk.chunk_index,
                chunk.content, chunk.section_name, chunk.token_count
            ))
        self.db.commit()

    def _generate_citation_key(self, parsed: ParsedDocument) -> str:
        author = parsed.authors.split(',')[0].split('&')[0].strip() if parsed.authors else "Unknown"
        year = parsed.year or "n.d."
        title_short = parsed.title[:30] if parsed.title else "Untitled"
        return f"{author} ({year}). {title_short}"

    def _update_registry(self, collection: str, doc_id: str, file_path: str):
        if collection not in self.registry["collections"]:
            self.registry["collections"][collection] = {
                "documents": [], "count": 0, "last_updated": ""
            }
        coll = self.registry["collections"][collection]
        if doc_id not in [d["id"] for d in coll["documents"]]:
            coll["documents"].append({"id": doc_id, "path": file_path})
            coll["count"] = len(coll["documents"])
        coll["last_updated"] = datetime.now().isoformat()
        self.registry["stats"]["total_documents"] = sum(
            c["count"] for c in self.registry["collections"].values()
        )
        self._save_registry()

    def get_stats(self) -> dict:
        """Get indexing statistics."""
        cursor = self.db.execute("""
            SELECT source_collection, COUNT(*) as count,
                   SUM(chunk_count) as total_chunks
            FROM documents GROUP BY source_collection
        """)
        collections = {}
        for row in cursor.fetchall():
            collections[row[0]] = {"documents": row[1], "chunks": row[2] or 0}

        return {
            "total_documents": sum(c["documents"] for c in collections.values()),
            "total_chunks": sum(c["chunks"] for c in collections.values()),
            "collections": collections,
        }

    def search_metadata(self, query: str = "", discipline: str = "",
                       doc_type: str = "", year_from: int = 0,
                       year_to: int = 9999, limit: int = 50) -> list:
        """Search documents in metadata database."""
        conditions = []
        params = []

        if query:
            conditions.append("(title LIKE ? OR authors LIKE ? OR keywords LIKE ?)")
            params.extend([f"%{query}%"] * 3)
        if discipline:
            conditions.append("discipline = ?")
            params.append(discipline)
        if doc_type:
            conditions.append("doc_type = ?")
            params.append(doc_type)
        if year_from > 0:
            conditions.append("year >= ?")
            params.append(year_from)
        if year_to < 9999:
            conditions.append("year <= ?")
            params.append(year_to)

        where = " AND ".join(conditions) if conditions else "1=1"
        cursor = self.db.execute(
            f"SELECT * FROM documents WHERE {where} ORDER BY year DESC LIMIT ?",
            params + [limit]
        )

        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def close(self):
        """Close database connection."""
        self.db.close()
