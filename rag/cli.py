#!/usr/bin/env python3
"""
Academic RAG CLI — Command-line interface for indexing and searching.

Usage:
    academic-rag index ./papers/ --collection papers --doc-type paper
    academic-rag search "transformer attention mechanism" --top-k 10
    academic-rag stats
    academic-rag build-vectors --batch 32
"""
import argparse
import sys
from pathlib import Path


def cmd_index(args):
    """Index documents from a directory."""
    from .indexer import DocumentIndexer

    indexer = DocumentIndexer()
    try:
        if args.file:
            result = indexer.index_document(
                args.file, args.collection, args.doc_type, args.discipline
            )
            status = result["status"]
            if status == "success":
                print(f"Indexed: {result['title']} ({result['chunks']} chunks)")
            elif status == "skipped":
                print(f"Skipped (already indexed): {args.file}")
            else:
                print(f"Error: {result.get('reason', 'unknown')}")
        else:
            directory = args.directory or "."
            print(f"Indexing {directory} into collection '{args.collection}'...")
            results = indexer.index_collection(args.collection, directory)
            print(f"\nDone: {results['success']} indexed, "
                  f"{results['skipped']} skipped, {results['error']} errors")
    finally:
        indexer.close()


def cmd_search(args):
    """Search the indexed documents."""
    from .retriever import MultiSourceRetriever

    retriever = MultiSourceRetriever()
    try:
        sources = args.sources.split(",") if args.sources else None
        results = retriever.retrieve(
            args.query, sources=sources,
            top_k=args.top_k, context_layer=args.layer
        )

        if not results:
            print("No results found.")
            return

        print(f"Found {len(results)} results:\n")
        for i, r in enumerate(results, 1):
            year = f" ({r.year})" if r.year else ""
            print(f"  {i}. [{r.score:.3f}] {r.title}{year}")
            if r.authors:
                print(f"     Authors: {r.authors}")
            if r.citation_key:
                print(f"     Cite: {r.citation_key}")
            if args.layer != "index" and r.content:
                preview = r.content[:200].replace("\n", " ")
                print(f"     {preview}...")
            print()
    finally:
        retriever.close()


def cmd_stats(args):
    """Show indexing statistics."""
    from .indexer import DocumentIndexer

    indexer = DocumentIndexer()
    try:
        stats = indexer.get_stats()
        print("=== Index Statistics ===")
        print(f"  Total documents: {stats['total_documents']}")
        print(f"  Total chunks:    {stats['total_chunks']}")
        if stats["collections"]:
            print("\n  Collections:")
            for name, info in stats["collections"].items():
                print(f"    {name}: {info['documents']} docs, {info['chunks']} chunks")
        else:
            print("\n  No documents indexed yet.")
    finally:
        indexer.close()


def cmd_build_vectors(args):
    """Build or update vector index."""
    # Import from scripts
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
    from build_vector_index import build_index, update_index

    if args.full:
        build_index(args.batch)
    else:
        update_index(args.batch)


def main():
    parser = argparse.ArgumentParser(
        prog="academic-rag",
        description="Academic RAG — Literature retrieval system"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # index
    p_index = subparsers.add_parser("index", help="Index documents")
    p_index.add_argument("directory", nargs="?", help="Directory to index")
    p_index.add_argument("-f", "--file", help="Single file to index")
    p_index.add_argument("-c", "--collection", default="papers", help="Collection name")
    p_index.add_argument("-t", "--doc-type", default="paper", help="Document type")
    p_index.add_argument("-d", "--discipline", default="general", help="Discipline")
    p_index.set_defaults(func=cmd_index)

    # search
    p_search = subparsers.add_parser("search", help="Search indexed documents")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("-k", "--top-k", type=int, default=10, help="Number of results")
    p_search.add_argument("-s", "--sources", help="Comma-separated source collections")
    p_search.add_argument("-l", "--layer", default="abstract",
                          choices=["index", "abstract", "detail"],
                          help="Content depth level")
    p_search.set_defaults(func=cmd_search)

    # stats
    p_stats = subparsers.add_parser("stats", help="Show index statistics")
    p_stats.set_defaults(func=cmd_stats)

    # build-vectors
    p_vectors = subparsers.add_parser("build-vectors", help="Build vector index")
    p_vectors.add_argument("--full", action="store_true", help="Full rebuild")
    p_vectors.add_argument("--batch", type=int, default=32, help="Batch size")
    p_vectors.set_defaults(func=cmd_build_vectors)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
