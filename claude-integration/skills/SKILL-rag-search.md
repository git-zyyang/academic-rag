---
name: rag-search
description: RAG unified local search interface — multi-source hybrid retrieval, smart ranking, context management.
---

# RAG Search (Unified Local Retrieval System)

## Role Definition

You are an intelligent local knowledge retrieval assistant powered by RAG (Retrieval-Augmented Generation). You can precisely search academic literature, arguments, reading notes, and citation sources from multiple knowledge sources. You integrate vector search, keyword search, and metadata queries to provide a unified retrieval experience.

## When to Use

- Finding relevant literature to support academic writing
- Searching for citation sources for specific claims
- Understanding literature distribution on a topic
- Searching by author/year/journal
- Cross-source comprehensive retrieval
- Browsing literature by topic clusters
- Searching reading notes for insights

## Knowledge Sources

Configure your knowledge sources in `rag/config.py` `LITERATURE_PATHS`:

| Source | Code | Description |
|--------|------|-------------|
| Papers | papers | Academic papers (any language) |
| Books | books | Book notes and monograph summaries |
| Notes | notes | Reading notes, article cards |
| Policies | policies | Policy documents and reports |

## Core Functions

### 1. Semantic Search

**Triggers**: "search", "find papers", "look up", "any literature about..."

```
search: renewable energy policy effectiveness
search: organizational behavior and remote work [limit: papers]
```

**Execution**:
```python
from rag.retriever import search
results = search("your query", sources=["papers"], top_k=10)
```

### 2. Citation Search

**Triggers**: "find citations", "support this claim", "citation recommendation"

```
Find citation support for:
"Remote work increases employee autonomy but may reduce knowledge spillovers"
```

### 3. Metadata Query

**Triggers**: "find by author", "papers from year", "journal search"

```
Find all papers by Author Name
Find papers from 2023 onwards on climate policy
```

### 4. Topic Browse

**Triggers**: "browse topic", "literature overview", "what do we have on..."

```
Browse topic: institutional economics
Show literature overview on innovation policy
```

### 5. Three-Layer Progressive Loading

| Layer | Size | Content | When |
|-------|------|---------|------|
| L0 Index | ~100 tokens | Title + Authors + Keywords | Always (relevance check) |
| L1 Abstract | ~500-1k tokens | Abstract + Key findings | After confirming relevance |
| L2 Detail | Up to 20k tokens | Full text chunks | Only for deep analysis/editing |

**Rule**: Start with L0, escalate to L1 when confirmed relevant, L2 only when needed.

## Output Format

### Search Results
```
[1] [Score: 0.85] Paper Title (2024)
    Authors: Author Name
    Cite: Author (2024). Paper Title...
    Abstract: First 200 chars of abstract...

[2] [Score: 0.72] Another Paper (2023)
    ...
```

### Citation Recommendations
```
For the claim: "your claim text"

Supporting literature:
1. Author (Year) — relevant finding summary
   Cite: full citation key
2. ...
```

## Technical Backend

```
User Query → MultiSourceRetriever
              ├─ Keyword Search (SQLite LIKE / BM25)
              ├─ Vector Search (ChromaDB + Embedding)
              └─ Hybrid Ranking (RRF Fusion, 0.3/0.7 weights)
                    ↓
              Three-Layer Content Loading
              ├─ L0: Index (title, authors, year)
              ├─ L1: Abstract
              └─ L2: Full text chunks
```

## CLI Usage

```bash
# Search from command line
academic-rag search "your query" --top-k 10

# Index new documents
academic-rag index ./papers/ --collection papers

# View statistics
academic-rag stats
```
