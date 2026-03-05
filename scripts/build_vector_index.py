#!/usr/bin/env python3
"""
Vector Index Builder
Build or incrementally update ChromaDB vector index from the metadata database.

Usage:
    python build_vector_index.py              # Incremental update (default)
    python build_vector_index.py --full       # Full rebuild
    python build_vector_index.py --batch 64   # Custom batch size

Environment variables:
    EMBEDDING_PROVIDER     openai | sentence-transformers (default: openai)
    EMBEDDING_MODEL        Model name (default: text-embedding-3-small)
    EMBEDDING_API_BASE     API endpoint (default: https://api.openai.com/v1)
    EMBEDDING_API_KEY      API key
    EMBEDDING_DIMENSION    Vector dimension (auto-detected if not set)
"""
import sqlite3
import time
from pathlib import Path
import sys

# Allow running as standalone script
sys.path.insert(0, str(Path(__file__).parent.parent))

from rag.config import STORES_DIR, VECTOR_DB_DIR
from rag.embeddings import get_provider

METADATA_DB = STORES_DIR / "metadata.db"


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Get embeddings using the configured provider."""
    provider = get_provider()
    return provider.embed(texts)


def _get_db_chunk_ids() -> set:
    """Get all valid chunk IDs from metadata.db."""
    conn = sqlite3.connect(str(METADATA_DB))
    cursor = conn.execute(
        "SELECT id FROM chunks WHERE content IS NOT NULL AND length(content) > 10"
    )
    ids = {row[0] for row in cursor.fetchall()}
    conn.close()
    return ids


def _get_vector_chunk_ids(collection) -> set:
    """Get existing chunk IDs from ChromaDB."""
    result = collection.get(include=[])
    return set(result["ids"]) if result["ids"] else set()


def _fetch_chunks_by_ids(chunk_ids: list) -> list:
    """Fetch chunk data from metadata.db."""
    if not chunk_ids:
        return []
    conn = sqlite3.connect(str(METADATA_DB))
    conn.row_factory = sqlite3.Row
    placeholders = ",".join(["?"] * len(chunk_ids))
    cursor = conn.execute(f"""
        SELECT c.id, c.document_id, c.content, c.section_name, c.chunk_index,
               d.title, d.authors, d.year, d.source_collection, d.language
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE c.id IN ({placeholders})
        ORDER BY c.id
    """, chunk_ids)
    rows = cursor.fetchall()
    conn.close()
    return rows


def _embed_and_add(rows, collection, batch_size: int):
    """Batch embed and insert into ChromaDB."""
    total = len(rows)
    start_time = time.time()
    indexed = 0
    errors = 0

    for i in range(0, total, batch_size):
        batch = rows[i : i + batch_size]
        ids, documents, metadatas = [], [], []

        for row in batch:
            content = row["content"].strip()
            if not content:
                continue
            ids.append(row["id"])
            documents.append(content)
            metadatas.append({
                "document_id": row["document_id"],
                "title": row["title"] or "",
                "authors": row["authors"] or "",
                "year": row["year"] or 0,
                "source_collection": row["source_collection"] or "",
                "section_name": row["section_name"] or "",
                "chunk_index": row["chunk_index"] or 0,
                "language": row["language"] or "zh",
            })

        if not ids:
            continue

        for attempt in range(3):
            try:
                embeddings = get_embeddings(documents)
                break
            except Exception as e:
                if attempt < 2:
                    wait = 2 ** (attempt + 1)
                    print(f"\n  API error, retrying in {wait}s: {e}")
                    time.sleep(wait)
                else:
                    print(f"\n  Skipping batch: {e}")
                    errors += len(ids)
                    embeddings = None

        if embeddings is None:
            continue

        collection.add(
            ids=ids, documents=documents,
            metadatas=metadatas, embeddings=embeddings,
        )
        indexed += len(ids)

        elapsed = time.time() - start_time
        speed = indexed / elapsed if elapsed > 0 else 0
        print(
            f"  Progress: {indexed}/{total} ({indexed*100//total}%) | "
            f"Speed: {speed:.0f} chunks/s | Elapsed: {elapsed:.1f}s",
            end="\r",
        )

    elapsed = time.time() - start_time
    print(f"\n  Done: {indexed} indexed, {errors} errors, {elapsed:.1f}s")
    return indexed, errors


def update_index(batch_size: int = 32):
    """Incremental update — only process new/deleted chunks."""
    import chromadb

    print("=== Vector Index Incremental Update ===")

    provider = get_provider()
    dim = provider.dimension()
    print(f"  Embedding provider ready, dimension: {dim}")

    VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)
    chroma_client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))

    try:
        collection = chroma_client.get_collection("academic_chunks")
        print(f"  Existing vectors: {collection.count()}")
    except Exception:
        print("  No existing collection found, running full build...")
        return build_index(batch_size)

    db_ids = _get_db_chunk_ids()
    vec_ids = _get_vector_chunk_ids(collection)

    new_ids = db_ids - vec_ids
    stale_ids = vec_ids - db_ids

    print(f"\n  metadata.db: {len(db_ids)} chunks")
    print(f"  ChromaDB:    {len(vec_ids)} vectors")
    print(f"  New:         {len(new_ids)}")
    print(f"  Stale:       {len(stale_ids)}")

    if not new_ids and not stale_ids:
        print("\n  Vector index is up to date.")
        return 0

    if stale_ids:
        stale_list = list(stale_ids)
        for i in range(0, len(stale_list), 500):
            batch = stale_list[i:i+500]
            collection.delete(ids=batch)
        print(f"  Deleted {len(stale_ids)} stale records")

    if new_ids:
        print(f"\n  Indexing {len(new_ids)} new chunks...")
        rows = _fetch_chunks_by_ids(list(new_ids))
        indexed, errors = _embed_and_add(rows, collection, batch_size)
    else:
        indexed = 0

    final_count = collection.count()
    print(f"\n=== Update Complete ===")
    print(f"  ChromaDB total: {final_count}")
    return indexed


def build_index(batch_size: int = 32):
    """Full rebuild of the vector index."""
    import chromadb

    provider = get_provider()
    dim = provider.dimension()

    print("=== Vector Index Full Build ===")
    print(f"  Embedding dimension: {dim}")

    VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)
    chroma_client = chromadb.PersistentClient(path=str(VECTOR_DB_DIR))

    try:
        chroma_client.delete_collection("academic_chunks")
        print("  Deleted old collection")
    except Exception:
        pass

    collection = chroma_client.create_collection(
        name="academic_chunks",
        metadata={
            "description": "Academic document chunk vectors",
            "embedding_dim": dim,
        },
    )

    conn = sqlite3.connect(str(METADATA_DB))
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("""
        SELECT c.id, c.document_id, c.content, c.section_name, c.chunk_index,
               d.title, d.authors, d.year, d.source_collection, d.language
        FROM chunks c
        JOIN documents d ON c.document_id = d.id
        WHERE c.content IS NOT NULL AND length(c.content) > 10
        ORDER BY c.id
    """)
    rows = cursor.fetchall()
    conn.close()
    print(f"  Total chunks: {len(rows)}")

    indexed, errors = _embed_and_add(rows, collection, batch_size)

    final_count = collection.count()
    print(f"\n=== Full Build Complete ===")
    print(f"  ChromaDB total: {final_count}")
    return indexed


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Build/update vector index")
    parser.add_argument("--full", action="store_true", help="Full rebuild (default: incremental)")
    parser.add_argument("--batch", type=int, default=32, help="Batch size")
    args = parser.parse_args()

    if args.full:
        build_index(args.batch)
    else:
        update_index(args.batch)
