# Academic RAG

**Academic literature retrieval system with hybrid search (BM25 + Vector + RRF), smart chunking, and Claude Code integration.**

Built for researchers who need a local knowledge base that actually understands academic document structure — section-aware chunking, three-layer progressive loading, and multi-format parsing (PDF/DOCX/Markdown/TXT) with automatic Chinese/English detection.

## Features

- **Multi-format parsing** — PDF (PyMuPDF), DOCX (python-docx), Markdown, TXT with CN/EN auto-detection
- **Structure-aware chunking** — 7 document type strategies (paper, book, policy, speech, deep-read, reading card, knowledge index)
- **Hybrid search** — BM25 keyword + semantic vector + Reciprocal Rank Fusion (0.3/0.7 weights)
- **Three-layer progressive loading** — Index (100 tokens) → Abstract (1k tokens) → Detail (20k tokens)
- **Multi-backend embeddings** — OpenAI / Qwen / DeepSeek / Ollama / local sentence-transformers
- **Claude Code integration** — 5 Skills for natural language access to your knowledge base
- **CLI tool** — Index, search, and manage from the command line

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    User Interface                    │
│  CLI (academic-rag)  │  Python API  │  Claude Skills │
├─────────────────────────────────────────────────────┤
│                MultiSourceRetriever                  │
│  ┌──────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │ Keyword  │  │    Vector    │  │     RRF       │  │
│  │ (SQLite) │  │  (ChromaDB)  │  │   Fusion      │  │
│  └──────────┘  └──────────────┘  └───────────────┘  │
├─────────────────────────────────────────────────────┤
│                  EmbeddingProvider                    │
│  OpenAI-compatible API  │  sentence-transformers     │
├─────────────────────────────────────────────────────┤
│  DocumentIndexer  │  AcademicChunker  │  PDFParser   │
│  (SQLite metadata)│  (7 strategies)   │  (4 formats) │
└─────────────────────────────────────────────────────┘
```

## Quick Start

### Install

```bash
git clone https://github.com/git-zyyang/academic-rag.git
cd academic-rag
pip install -e ".[all]"
```

### Configure Embeddings

```bash
cp .env.example .env
# Edit .env with your API key:
#   EMBEDDING_PROVIDER=openai
#   EMBEDDING_MODEL=text-embedding-3-small
#   EMBEDDING_API_KEY=sk-your-key
```

Or use local embeddings (no API key needed):
```bash
# In .env:
EMBEDDING_PROVIDER=sentence-transformers
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

### Index Your Documents

```bash
# Index a directory of papers
academic-rag index ./my-papers/ --collection papers --doc-type paper

# Index book notes
academic-rag index ./book-notes/ --collection books --doc-type book

# Build vector index (requires embedding provider)
academic-rag build-vectors
```

### Search

```bash
# Keyword + vector hybrid search
academic-rag search "digital economy and innovation" --top-k 10

# Search with detail level
academic-rag search "transformer attention" --layer detail

# View index statistics
academic-rag stats
```

## Python API

```python
from rag import DocumentIndexer, MultiSourceRetriever, search

# Index documents
indexer = DocumentIndexer()
indexer.index_document("paper.pdf", collection="papers", doc_type="paper")
indexer.index_collection("papers", "./papers/")
print(indexer.get_stats())
indexer.close()

# Search
results = search("digital economy productivity", top_k=5)
for r in results:
    print(f"[{r.score:.3f}] {r.title} ({r.year})")
    print(f"  {r.content[:100]}...")

# Advanced: custom retriever with source filtering
retriever = MultiSourceRetriever()
results = retriever.retrieve(
    "innovation policy",
    sources=["papers", "policies"],
    top_k=10,
    context_layer="abstract"  # index | abstract | detail
)
retriever.close()
```

### Custom Embedding Provider

```python
from rag.embeddings import EmbeddingFactory, set_provider

# Use Qwen via aiping.cn
provider = EmbeddingFactory.create(
    "openai",
    model="Qwen3-Embedding-8B",
    api_base="https://aiping.cn/api/v1",
    api_key="your-key"
)
set_provider(provider)

# Or use local sentence-transformers
provider = EmbeddingFactory.create(
    "sentence-transformers",
    model="paraphrase-multilingual-MiniLM-L12-v2"
)
set_provider(provider)
```

## Use Cases

### 1. Finding Citations for a Claim

```python
from rag import MultiSourceRetriever

retriever = MultiSourceRetriever()
results = retriever.retrieve_for_citation(
    "AI enhances productivity through automation and augmentation"
)
for r in results:
    print(f"  {r.citation_key}")
    print(f"  {r.content[:200]}")
```

### 2. Building a Literature Review

```python
from rag import search

# Search from multiple angles
queries = [
    "digital economy measurement GDP",
    "ICT investment productivity paradox",
    "platform economy labor market"
]
all_results = []
for q in queries:
    all_results.extend(search(q, top_k=5))

# Deduplicate by doc_id
seen = set()
unique = [r for r in all_results if r.doc_id not in seen and not seen.add(r.doc_id)]
print(f"Found {len(unique)} unique papers across 3 queries")
```

### 3. Processing Reading Notes into RAG

```python
from rag import DocumentIndexer

indexer = DocumentIndexer()
# Index all markdown reading notes
results = indexer.index_collection("notes", "./reading-notes/")
print(f"Indexed {results['success']} notes, {results['skipped']} already existed")
indexer.close()
```

## Claude Code Integration

Copy the 5 Skills to your Claude Code project:

```bash
cp claude-integration/skills/*.md .claude/skills/
```

Then in Claude Code:
```
> Search my papers for digital economy and innovation
> Find citation support for: "AI empowers new productivity"
> Deep read this paper: ./papers/example.pdf
> Process my reading inbox
```

See [claude-integration/INTEGRATION.md](claude-integration/INTEGRATION.md) for detailed setup.

## Project Structure

```
academic-rag/
├── rag/                          # Core library
│   ├── __init__.py               # Public API
│   ├── config.py                 # Configuration
│   ├── embeddings.py             # Multi-backend embedding providers
│   ├── pdf_parser.py             # Document parsing (PDF/DOCX/MD/TXT)
│   ├── chunker.py                # Structure-aware chunking
│   ├── indexer.py                # SQLite indexing pipeline
│   ├── retriever.py              # Hybrid search (BM25 + Vector + RRF)
│   ├── reranker.py               # Cross-encoder reranking
│   └── cli.py                    # CLI entry point
├── scripts/                      # Utility scripts
│   └── build_vector_index.py     # Vector index builder
├── claude-integration/           # Claude Code integration
│   ├── skills/                   # 5 Claude Code Skills
│   ├── rules/                    # Behavior rules
│   └── INTEGRATION.md            # Setup guide
├── pyproject.toml                # Python project config
├── .env.example                  # Environment template
└── LICENSE                       # MIT
```

## Requirements

- Python 3.10+
- Core: `openai` (for API-based embeddings)
- PDF parsing: `pymupdf` (optional)
- DOCX parsing: `python-docx` (optional)
- Vector search: `chromadb` (optional — keyword search works without it)
- Local embeddings: `sentence-transformers` (optional)

## Contributing

Contributions welcome! Please open an issue or PR.

## Support

If you find this useful, consider starring the repo.

<a href="assets/donate_alipay.jpg"><img src="assets/donate_alipay.jpg" width="200" alt="Support via Alipay"></a>

## License

MIT License. See [LICENSE](LICENSE).
