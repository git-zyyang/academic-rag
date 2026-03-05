"""
Academic RAG System Configuration
Configure via environment variables, .env file, or config.yaml.
"""
import os
from pathlib import Path

# ============================================
# Path Configuration
# ============================================
PROJECT_ROOT = Path(os.environ.get("RAG_PROJECT_ROOT", Path(__file__).parent.parent))
RAG_ROOT = Path(__file__).parent

# Storage paths
STORES_DIR = RAG_ROOT / "stores"
METADATA_DB_PATH = STORES_DIR / "metadata.db"
INDEX_REGISTRY_PATH = STORES_DIR / "index_registry.json"
VECTOR_DB_DIR = STORES_DIR / "vector_db"

# Literature source paths — customize for your project
# Override by setting RAG_LITERATURE_PATHS in your config or code.
LITERATURE_PATHS = {
    "papers": PROJECT_ROOT / "papers",
    "books": PROJECT_ROOT / "books",
    "notes": PROJECT_ROOT / "notes",
    "policies": PROJECT_ROOT / "policies",
}

# ============================================
# Embedding Configuration
# ============================================
# Configure via environment variables:
#   EMBEDDING_PROVIDER=openai | sentence-transformers
#   EMBEDDING_MODEL=text-embedding-3-small
#   EMBEDDING_API_BASE=https://api.openai.com/v1
#   EMBEDDING_API_KEY=sk-xxx
#   EMBEDDING_DIMENSION=1536
EMBEDDING_CONFIG = {
    "provider": os.environ.get("EMBEDDING_PROVIDER", "openai"),
    "model_name": os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small"),
    "api_base": os.environ.get("EMBEDDING_API_BASE", "https://api.openai.com/v1"),
    "dimension": int(os.environ.get("EMBEDDING_DIMENSION", "1536")),
}

# ============================================
# Chunking Configuration
# ============================================
CHUNKING_CONFIG = {
    "academic_paper": {
        "chunk_size": 1000,       # characters
        "chunk_overlap": 200,     # overlap characters
        "separator": "\n\n",
        "section_aware": True,
    },
    "book_notes": {
        "chunk_size": 800,
        "chunk_overlap": 150,
        "separator": "\n\n",
        "section_aware": True,
    },
    "policy_document": {
        "chunk_size": 600,
        "chunk_overlap": 100,
        "separator": "\n",
        "section_aware": True,
    },
    "speech": {
        "chunk_size": 500,
        "chunk_overlap": 100,
        "separator": "\n\n",
        "section_aware": False,
    },
    "deep_read_note": {
        "chunk_size": 1200,
        "chunk_overlap": 100,
        "separator": "## ",
        "section_aware": True,
    },
    "reading_card": {
        "chunk_size": 800,
        "chunk_overlap": 100,
        "separator": "## ",
        "section_aware": True,
    },
    "knowledge_index": {
        "chunk_size": 600,
        "chunk_overlap": 100,
        "separator": "## ",
        "section_aware": True,
    },
}

# ============================================
# Retrieval Configuration
# ============================================
RETRIEVAL_CONFIG = {
    "default_top_k": 10,
    "similarity_threshold": 0.3,
    "use_reranker": True,
    "reranker_model": "BAAI/bge-reranker-large",
    "hybrid_search": True,
    "bm25_weight": 0.3,          # BM25 keyword weight
    "vector_weight": 0.7,        # Vector search weight
}

# ============================================
# Context Budget (for three-layer progressive loading)
# ============================================
CONTEXT_BUDGET = {
    "index_layer": 500,      # tokens per doc — index layer
    "abstract_layer": 1500,  # tokens per doc — abstract layer
    "detail_layer": 20000,   # tokens per doc — detail layer
    "max_total": 100000,     # max total tokens per retrieval
}

# ============================================
# Metadata Database Schema (SQLite)
# ============================================
METADATA_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    authors TEXT,
    year INTEGER,
    journal_or_publisher TEXT,
    keywords TEXT,
    discipline TEXT DEFAULT 'general',
    topic_cluster TEXT,
    language TEXT DEFAULT 'zh',
    doc_type TEXT,  -- paper, book, policy, note, etc.
    file_path TEXT,
    chunk_count INTEGER DEFAULT 0,
    indexed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    abstract TEXT,
    citation_key TEXT,
    source_collection TEXT
);

CREATE INDEX IF NOT EXISTS idx_discipline ON documents(discipline);
CREATE INDEX IF NOT EXISTS idx_topic ON documents(topic_cluster);
CREATE INDEX IF NOT EXISTS idx_doc_type ON documents(doc_type);
CREATE INDEX IF NOT EXISTS idx_year ON documents(year);
CREATE INDEX IF NOT EXISTS idx_language ON documents(language);

CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    chunk_index INTEGER,
    content TEXT,
    section_name TEXT,
    page_range TEXT,
    token_count INTEGER,
    FOREIGN KEY (document_id) REFERENCES documents(id)
);

CREATE INDEX IF NOT EXISTS idx_chunk_doc ON chunks(document_id);
"""

# ============================================
# Supported File Formats
# ============================================
SUPPORTED_FORMATS = {
    ".pdf": "PDF document",
    ".docx": "Word document",
    ".md": "Markdown document",
    ".txt": "Plain text",
}
