"""
Academic RAG — Retrieval-Augmented Generation for academic literature.
Hybrid search (BM25 + Vector + RRF), smart chunking, and multi-format parsing.
"""

from .pdf_parser import PDFParser, ParsedDocument, parse_document, batch_parse
from .chunker import AcademicChunker, Chunk, chunk_document
from .indexer import DocumentIndexer
from .retriever import MultiSourceRetriever, RetrievalResult, search
from .reranker import Reranker, SimpleReranker
from .embeddings import (
    EmbeddingProvider, EmbeddingFactory,
    OpenAICompatibleProvider, SentenceTransformerProvider,
    get_provider, set_provider,
)

__all__ = [
    # Parser
    "PDFParser", "ParsedDocument", "parse_document", "batch_parse",
    # Chunker
    "AcademicChunker", "Chunk", "chunk_document",
    # Indexer
    "DocumentIndexer",
    # Retriever
    "MultiSourceRetriever", "RetrievalResult", "search",
    # Reranker
    "Reranker", "SimpleReranker",
    # Embeddings
    "EmbeddingProvider", "EmbeddingFactory",
    "OpenAICompatibleProvider", "SentenceTransformerProvider",
    "get_provider", "set_provider",
]

__version__ = "1.0.0"
