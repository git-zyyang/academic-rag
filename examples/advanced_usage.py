#!/usr/bin/env python3
"""
Advanced Usage Examples — Custom embedding providers, filtering, reranking.
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))


def example_custom_embedding():
    """Use a custom embedding provider."""
    from rag.embeddings import EmbeddingFactory, set_provider

    # Option 1: OpenAI
    provider = EmbeddingFactory.create(
        "openai",
        model="text-embedding-3-small",
        api_key="sk-your-key",
    )

    # Option 2: Local sentence-transformers (no API key needed)
    provider = EmbeddingFactory.create(
        "sentence-transformers",
        model="all-MiniLM-L6-v2",
    )

    # Set as default for all RAG operations
    set_provider(provider)
    print(f"Embedding dimension: {provider.dimension()}")


def example_filtered_search():
    """Search with source and year filters."""
    from rag import MultiSourceRetriever

    retriever = MultiSourceRetriever()

    # Search only in papers collection
    results = retriever.retrieve(
        "machine learning applications",
        sources=["papers"],
        top_k=10,
        context_layer="abstract"
    )
    print(f"Found {len(results)} results in papers collection")

    # Search by topic cluster
    results = retriever.retrieve_by_topic("innovation", top_k=20)
    print(f"Found {len(results)} results for topic 'innovation'")

    # Search with metadata filters
    from rag import DocumentIndexer
    indexer = DocumentIndexer()
    docs = indexer.search_metadata(
        query="supply chain resilience",
        year_from=2020,
        doc_type="paper",
        limit=10
    )
    print(f"Found {len(docs)} papers about supply chain resilience since 2020")
    indexer.close()
    retriever.close()


def example_reranking():
    """Apply cross-encoder reranking to search results."""
    from rag import search, Reranker, SimpleReranker

    query = "remote work and organizational performance"
    results = search(query, top_k=20)

    # Option 1: Cross-encoder reranking (requires sentence-transformers)
    try:
        reranker = Reranker()
        reranked = reranker.rerank(query, results, top_k=5)
        print("Cross-encoder reranked results:")
        for r in reranked:
            print(f"  [{r.score:.3f}] {r.title}")
    except ImportError:
        print("sentence-transformers not installed, using simple reranker")

    # Option 2: Simple keyword reranker (no dependencies)
    simple_reranker = SimpleReranker()
    reranked = simple_reranker.rerank(query, results, top_k=5)
    print("Simple reranked results:")
    for r in reranked:
        print(f"  [{r.score:.3f}] {r.title}")


def example_citation_search():
    """Find citable literature for a specific claim."""
    from rag import MultiSourceRetriever

    retriever = MultiSourceRetriever()
    claim = "Supply chain diversification reduces vulnerability to trade shocks"
    results = retriever.retrieve_for_citation(claim, top_k=5)

    print(f"Citations for: '{claim}'")
    for r in results:
        print(f"  {r.citation_key}")
        print(f"    {r.content[:150]}...")
    retriever.close()


if __name__ == "__main__":
    print("=== Example 1: Custom Embedding ===")
    # example_custom_embedding()  # Uncomment and set your API key
    print("  (uncomment to run)")

    print("\n=== Example 2: Filtered Search ===")
    example_filtered_search()

    print("\n=== Example 3: Reranking ===")
    example_reranking()

    print("\n=== Example 4: Citation Search ===")
    example_citation_search()
