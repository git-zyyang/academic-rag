"""
Multi-source Retriever — Unified search interface
Supports keyword search (BM25-like), vector search (ChromaDB), and hybrid search (RRF fusion).
"""
import sqlite3
from typing import Optional
from dataclasses import dataclass, field

from .config import METADATA_DB_PATH, RETRIEVAL_CONFIG, VECTOR_DB_DIR
from .embeddings import get_provider


@dataclass
class RetrievalResult:
    """Search result."""
    doc_id: str
    title: str
    authors: str = ""
    year: Optional[int] = None
    content: str = ""
    section_name: str = ""
    score: float = 0.0
    citation_key: str = ""
    source_collection: str = ""
    metadata: dict = field(default_factory=dict)


class MultiSourceRetriever:
    """Multi-source hybrid retriever with BM25 + Vector + RRF fusion."""

    def __init__(self, db_path: str = ""):
        db = db_path or str(METADATA_DB_PATH)
        self.db = sqlite3.connect(db)
        self.db.row_factory = sqlite3.Row
        self.config = RETRIEVAL_CONFIG
        self._vector_index = None
        self._chroma_client = None

    def retrieve(self, query: str, sources: Optional[list] = None,
                 top_k: int = 10, context_layer: str = "abstract") -> list:
        """
        Unified retrieval interface.

        Args:
            query: Search query
            sources: Limit to specific collections (None = all)
            top_k: Number of results to return
            context_layer: Content depth — index | abstract | detail

        Returns:
            list[RetrievalResult]: Ranked results
        """
        # 1. Keyword search (SQLite full-text)
        keyword_results = self._keyword_search(query, sources, top_k * 2)

        # 2. Vector search (if available)
        vector_results = []
        if self._has_vector_index():
            vector_results = self._vector_search(query, sources, top_k * 2)

        # 3. Hybrid ranking (RRF)
        if vector_results and keyword_results:
            merged = self._reciprocal_rank_fusion(
                keyword_results, vector_results,
                keyword_weight=self.config["bm25_weight"],
                vector_weight=self.config["vector_weight"]
            )
        elif vector_results:
            merged = vector_results
        else:
            merged = keyword_results

        # 4. Truncate to top_k
        results = merged[:top_k]

        # 5. Fill content based on context layer
        results = self._fill_content(results, context_layer)

        return results

    def retrieve_by_topic(self, topic: str, top_k: int = 20) -> list:
        """Retrieve by topic cluster."""
        cursor = self.db.execute("""
            SELECT d.*, GROUP_CONCAT(c.content, '\n') as full_content
            FROM documents d
            LEFT JOIN chunks c ON d.id = c.document_id
            WHERE d.topic_cluster LIKE ? OR d.keywords LIKE ?
            GROUP BY d.id
            ORDER BY d.year DESC
            LIMIT ?
        """, (f"%{topic}%", f"%{topic}%", top_k))

        results = []
        for row in cursor.fetchall():
            results.append(RetrievalResult(
                doc_id=row["id"],
                title=row["title"] or "",
                authors=row["authors"] or "",
                year=row["year"],
                content=row["abstract"] or "",
                citation_key=row["citation_key"] or "",
                source_collection=row["source_collection"] or "",
            ))
        return results

    def retrieve_for_citation(self, claim: str, top_k: int = 5) -> list:
        """Retrieve citable literature for a specific claim."""
        results = self.retrieve(claim, top_k=top_k, context_layer="abstract")
        return [r for r in results if r.citation_key]

    def get_document_detail(self, doc_id: str) -> Optional[dict]:
        """Get full document details including all chunks."""
        cursor = self.db.execute(
            "SELECT * FROM documents WHERE id = ?", (doc_id,)
        )
        doc = cursor.fetchone()
        if not doc:
            return None

        chunks_cursor = self.db.execute(
            "SELECT * FROM chunks WHERE document_id = ? ORDER BY chunk_index",
            (doc_id,)
        )
        chunks = [dict(row) for row in chunks_cursor.fetchall()]

        return {
            "document": dict(doc),
            "chunks": chunks,
            "full_text": "\n\n".join(c["content"] for c in chunks if c["content"]),
        }

    def _keyword_search(self, query: str, sources: Optional[list],
                       limit: int) -> list:
        """Keyword search (SQLite LIKE-based)."""
        conditions = []
        params = []

        keywords = query.replace('\uff0c', ' ').replace(',', ' ').split()
        keyword_conditions = []
        for kw in keywords[:5]:
            keyword_conditions.append(
                "(d.title LIKE ? OR d.keywords LIKE ? OR d.abstract LIKE ? OR c.content LIKE ?)"
            )
            params.extend([f"%{kw}%"] * 4)

        if keyword_conditions:
            conditions.append("(" + " OR ".join(keyword_conditions) + ")")

        if sources:
            placeholders = ",".join(["?"] * len(sources))
            conditions.append(f"d.source_collection IN ({placeholders})")
            params.extend(sources)

        where = " AND ".join(conditions) if conditions else "1=1"

        cursor = self.db.execute(f"""
            SELECT DISTINCT d.id, d.title, d.authors, d.year,
                   d.abstract, d.citation_key, d.source_collection,
                   c.content as chunk_content, c.section_name
            FROM documents d
            LEFT JOIN chunks c ON d.id = c.document_id
            WHERE {where}
            LIMIT ?
        """, params + [limit])

        results = []
        seen_docs = set()
        for row in cursor.fetchall():
            doc_id = row[0]
            if doc_id not in seen_docs:
                seen_docs.add(doc_id)
                score = sum(1 for kw in keywords
                           if kw in (row[1] or "") or kw in (row[4] or ""))
                results.append(RetrievalResult(
                    doc_id=doc_id,
                    title=row[1] or "",
                    authors=row[2] or "",
                    year=row[3],
                    content=row[7] or row[4] or "",
                    section_name=row[8] or "",
                    score=score / max(len(keywords), 1),
                    citation_key=row[5] or "",
                    source_collection=row[6] or "",
                ))

        results.sort(key=lambda x: x.score, reverse=True)
        return results

    def _has_vector_index(self) -> bool:
        """Check if a vector index is available (ChromaDB)."""
        if self._vector_index is not None:
            return True
        try:
            import chromadb
            if VECTOR_DB_DIR.exists():
                client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))
                collection = client.get_collection("academic_chunks")
                if collection.count() > 0:
                    self._vector_index = collection
                    self._chroma_client = client
                    return True
        except Exception:
            pass
        return False

    def _vector_search(self, query: str, sources: Optional[list],
                      limit: int) -> list:
        """Vector similarity search (ChromaDB + configurable embedding)."""
        if self._vector_index is None:
            return []

        where_filter = None
        if sources:
            if len(sources) == 1:
                where_filter = {"source_collection": sources[0]}
            else:
                where_filter = {"source_collection": {"$in": sources}}

        try:
            provider = get_provider()
            query_embedding = provider.embed([query])[0]
            results = self._vector_index.query(
                query_embeddings=[query_embedding],
                n_results=min(limit, 50),
                where=where_filter,
            )
        except Exception:
            return []

        retrieval_results = []
        if results and results["ids"] and results["ids"][0]:
            seen_docs = set()
            for i, chunk_id in enumerate(results["ids"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 1.0
                score = max(0, 1.0 - distance)
                doc_id = meta.get("document_id", "")

                if doc_id in seen_docs:
                    continue
                seen_docs.add(doc_id)

                content = results["documents"][0][i] if results["documents"] else ""
                retrieval_results.append(RetrievalResult(
                    doc_id=doc_id,
                    title=meta.get("title", ""),
                    authors=meta.get("authors", ""),
                    year=meta.get("year") or None,
                    content=content[:500],
                    section_name=meta.get("section_name", ""),
                    score=score,
                    source_collection=meta.get("source_collection", ""),
                ))

        retrieval_results.sort(key=lambda x: x.score, reverse=True)
        return retrieval_results

    def _reciprocal_rank_fusion(self, list1: list, list2: list,
                                keyword_weight: float = 0.3,
                                vector_weight: float = 0.7,
                                k: int = 60) -> list:
        """Reciprocal Rank Fusion (RRF) for merging ranked lists."""
        scores = {}

        for rank, result in enumerate(list1):
            doc_id = result.doc_id
            scores[doc_id] = scores.get(doc_id, {"result": result, "score": 0})
            scores[doc_id]["score"] += keyword_weight / (k + rank + 1)

        for rank, result in enumerate(list2):
            doc_id = result.doc_id
            if doc_id in scores:
                scores[doc_id]["score"] += vector_weight / (k + rank + 1)
            else:
                scores[doc_id] = {"result": result, "score": 0}
                scores[doc_id]["score"] += vector_weight / (k + rank + 1)

        merged = sorted(scores.values(), key=lambda x: x["score"], reverse=True)
        for item in merged:
            item["result"].score = item["score"]
        return [item["result"] for item in merged]

    def _fill_content(self, results: list, context_layer: str) -> list:
        """Fill content based on context layer (index/abstract/detail)."""
        for result in results:
            if context_layer == "index":
                result.content = f"{result.title} | {result.authors} ({result.year})"
            elif context_layer == "abstract":
                doc = self.db.execute(
                    "SELECT abstract FROM documents WHERE id = ?",
                    (result.doc_id,)
                ).fetchone()
                if doc and doc["abstract"]:
                    result.content = doc["abstract"]
            elif context_layer == "detail":
                detail = self.get_document_detail(result.doc_id)
                if detail:
                    result.content = detail["full_text"][:20000]

        return results

    def close(self):
        """Close database connection."""
        self.db.close()


def search(query: str, sources: Optional[list] = None,
           top_k: int = 10) -> list:
    """Convenience function: run a search."""
    retriever = MultiSourceRetriever()
    try:
        return retriever.retrieve(query, sources, top_k)
    finally:
        retriever.close()
