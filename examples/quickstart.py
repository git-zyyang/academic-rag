#!/usr/bin/env python3
"""
Quick Start Example — Index papers and run a search in 3 steps.
"""
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    from rag import DocumentIndexer, search

    # Step 1: Index some documents
    print("=== Step 1: Index Documents ===")
    indexer = DocumentIndexer()

    sample_dir = Path(__file__).parent / "sample_papers"
    if sample_dir.exists() and list(sample_dir.iterdir()):
        results = indexer.index_collection("papers", str(sample_dir))
        print(f"  Indexed: {results['success']}, Skipped: {results['skipped']}")
    else:
        print("  No sample papers found. Add PDF/DOCX/MD files to examples/sample_papers/")
        print("  Or index your own directory:")
        print("    academic-rag index /path/to/papers/ --collection papers")

    # Step 2: Check statistics
    print("\n=== Step 2: Index Statistics ===")
    stats = indexer.get_stats()
    print(f"  Total documents: {stats['total_documents']}")
    print(f"  Total chunks: {stats['total_chunks']}")
    for name, info in stats.get("collections", {}).items():
        print(f"    {name}: {info['documents']} docs, {info['chunks']} chunks")
    indexer.close()

    # Step 3: Search
    if stats["total_documents"] > 0:
        print("\n=== Step 3: Search ===")
        query = "economic growth and innovation"
        print(f"  Query: '{query}'")
        results = search(query, top_k=5)
        if results:
            for i, r in enumerate(results, 1):
                year = f" ({r.year})" if r.year else ""
                print(f"  {i}. [{r.score:.3f}] {r.title}{year}")
        else:
            print("  No results found.")
    else:
        print("\n=== Step 3: Search (skipped — no documents indexed) ===")

    print("\nDone! For more options, try: academic-rag --help")


if __name__ == "__main__":
    main()
